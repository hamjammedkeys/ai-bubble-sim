from fastapi import FastAPI
from pydantic import BaseModel, Field

from fragility_map.api.review import router as review_router
from fragility_map.api.scenario import router as scenario_router
from fragility_map.model.graph_export import build_graph_payload
from fragility_map.model.stress import (
    CompanyFinancials,
    NetworkRelationship,
    ScenarioConfig,
    run_cloud_spending_slowdown,
)

app = FastAPI(title="AI Fragility Map API")
app.include_router(review_router)
app.include_router(scenario_router)


class ScenarioRequest(BaseModel):
    shock_percentage: float = Field(default=0.30, ge=0.0, le=1.0)
    pass_through_rate: float = Field(default=0.80, ge=0.0, le=1.0)
    propagation_factor: float = Field(default=0.50, ge=0.0, le=1.0)
    max_rounds: int = Field(default=3, ge=1, le=3)


def demo_companies() -> dict[str, CompanyFinancials]:
    return {
        "msft": CompanyFinancials(
            "msft", "Microsoft", "cloud_platform", 245_000, 75_000, 97_000, 110_000, 2_000
        ),
        "amzn": CompanyFinancials(
            "amzn", "Amazon", "cloud_platform", 638_000, 89_000, 135_000, 68_000, 3_000
        ),
        "googl": CompanyFinancials(
            "googl", "Alphabet", "cloud_platform", 350_000, 110_000, 30_000, 115_000, 1_000
        ),
        "meta": CompanyFinancials(
            "meta", "Meta Platforms", "cloud_platform", 164_000, 70_000, 37_000, 70_000, 500
        ),
        "orcl": CompanyFinancials(
            "orcl", "Oracle", "cloud_platform", 53_000, 11_000, 88_000, 18_000, 4_000
        ),
        "nvda": CompanyFinancials(
            "nvda", "NVIDIA", "semiconductor", 130_000, 43_000, 11_000, 81_000, 250
        ),
        "amd": CompanyFinancials(
            "amd", "AMD", "semiconductor", 26_000, 6_000, 3_000, 1_900, 120
        ),
        "smci": CompanyFinancials(
            "smci", "Supermicro", "infrastructure", 15_000, 2_000, 2_000, 1_200, 80
        ),
        "anet": CompanyFinancials(
            "anet", "Arista Networks", "infrastructure", 7_000, 6_000, 0, 2_800, 0
        ),
        "vrt": CompanyFinancials(
            "vrt", "Vertiv", "infrastructure", 8_000, 800, 3_000, 1_000, 250
        ),
        "asml": CompanyFinancials(
            "asml", "ASML", "semiconductor_equipment", 30_000, 7_000, 5_000, 9_000, 100
        ),
        "amat": CompanyFinancials(
            "amat",
            "Applied Materials",
            "semiconductor_equipment",
            27_000,
            8_000,
            6_000,
            8_000,
            250,
        ),
    }


def demo_relationships() -> list[NetworkRelationship]:
    return [
        NetworkRelationship("msft-nvda", "msft", "nvda", 12_000, 0.6, "inferred"),
        NetworkRelationship("amzn-nvda", "amzn", "nvda", 10_000, 0.6, "inferred"),
        NetworkRelationship("googl-nvda", "googl", "nvda", 8_000, 0.6, "inferred"),
        NetworkRelationship("meta-nvda", "meta", "nvda", 9_000, 0.6, "inferred"),
        NetworkRelationship("orcl-nvda", "orcl", "nvda", 4_000, 0.6, "inferred"),
        NetworkRelationship("msft-smci", "msft", "smci", 3_000, 0.6, "inferred"),
        NetworkRelationship("amzn-anet", "amzn", "anet", 2_000, 0.6, "inferred"),
        NetworkRelationship("googl-vrt", "googl", "vrt", 1_500, 0.6, "inferred"),
        NetworkRelationship("nvda-asml", "nvda", "asml", 2_000, 0.3, "inferred"),
        NetworkRelationship("nvda-amat", "nvda", "amat", 1_500, 0.3, "inferred"),
    ]


@app.get("/api/graph")
def get_graph() -> dict:
    companies = demo_companies()
    relationships = demo_relationships()
    scenario = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(0.30, 0.80, 0.50, 3),
    )
    return build_graph_payload(companies, relationships, scenario)


@app.post("/api/scenario/cloud-slowdown")
def run_scenario(request: ScenarioRequest) -> dict:
    companies = demo_companies()
    relationships = demo_relationships()
    scenario = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(
            request.shock_percentage,
            request.pass_through_rate,
            request.propagation_factor,
            request.max_rounds,
        ),
    )
    return build_graph_payload(companies, relationships, scenario)
