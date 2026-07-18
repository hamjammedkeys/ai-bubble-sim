from fragility_map.model.graph_export import build_graph_payload
from fragility_map.model.stress import (
    CompanyFinancials,
    CompanyImpact,
    EdgePulse,
    NetworkRelationship,
    ScenarioResult,
)


def test_build_graph_payload_labels_estimates_and_status() -> None:
    companies = {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 100, 20, 10, 30, 1),
        "nvda": CompanyFinancials("nvda", "NVIDIA", "semiconductor", 50, 15, 5, 20, 1),
    }
    relationships = [NetworkRelationship("edge-1", "msft", "nvda", 10, 0.9, "percentage-derived")]
    scenario = ScenarioResult(
        {
            "msft": CompanyImpact("msft", 0, 0, 30, "stable"),
            "nvda": CompanyImpact("nvda", 2.4, 1.2, 18.8, "exposed"),
        },
        [EdgePulse("edge-1", "msft", "nvda", 0, 2.4)],
    )

    payload = build_graph_payload(companies, relationships, scenario)

    assert payload["nodes"][1]["data"]["label"] == "NVIDIA"
    assert payload["nodes"][1]["data"]["stressStatus"] == "exposed"
    assert payload["edges"][0]["data"]["estimateMethod"] == "percentage-derived"
    assert payload["summary"]["scenarioLanguage"] == "estimated impact under scenario"
