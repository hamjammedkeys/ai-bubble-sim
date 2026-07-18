from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyFinancials:
    company_id: str
    name: str
    sector_group: str
    revenue: float
    cash: float
    debt: float
    operating_income: float
    interest_expense: float


@dataclass(frozen=True)
class NetworkRelationship:
    relationship_id: str
    buyer_company_id: str
    seller_company_id: str
    annual_flow_base: float
    confidence_score: float
    estimation_method: str


@dataclass(frozen=True)
class ScenarioConfig:
    shock_percentage: float
    pass_through_rate: float
    propagation_factor: float
    max_rounds: int


@dataclass(frozen=True)
class EdgePulse:
    relationship_id: str
    buyer_company_id: str
    seller_company_id: str
    round_index: int
    revenue_loss: float


@dataclass(frozen=True)
class CompanyImpact:
    company_id: str
    revenue_loss: float
    operating_income_loss: float
    new_operating_income: float
    stress_status: str


@dataclass(frozen=True)
class ScenarioResult:
    company_impacts: dict[str, CompanyImpact]
    edge_pulses: list[EdgePulse]


def _stress_status(company: CompanyFinancials, revenue_loss: float) -> str:
    revenue_loss_ratio = revenue_loss / company.revenue if company.revenue else 0.0
    operating_income_loss = revenue_loss * 0.5
    new_operating_income = company.operating_income - operating_income_loss
    operating_income_decline = (
        operating_income_loss / company.operating_income if company.operating_income else 0.0
    )
    interest_coverage = (
        new_operating_income / company.interest_expense
        if company.interest_expense
        else float("inf")
    )
    if (
        new_operating_income < 0
        or interest_coverage < 2.0
        or operating_income_loss > company.cash * 0.25
    ):
        return "critical"
    if revenue_loss_ratio >= 0.08 or operating_income_decline >= 0.20:
        return "stressed"
    if revenue_loss_ratio >= 0.03:
        return "exposed"
    return "stable"


def run_cloud_spending_slowdown(
    companies: dict[str, CompanyFinancials],
    relationships: list[NetworkRelationship],
    config: ScenarioConfig,
) -> ScenarioResult:
    losses_by_company = {company_id: 0.0 for company_id in companies}
    edge_pulses: list[EdgePulse] = []
    active_shocks = {
        company_id: config.shock_percentage
        for company_id, company in companies.items()
        if company.sector_group == "cloud_platform"
    }
    for round_index in range(config.max_rounds):
        next_shocks: dict[str, float] = {}
        for relationship in relationships:
            buyer_shock = active_shocks.get(relationship.buyer_company_id, 0.0)
            if buyer_shock <= 0:
                continue
            revenue_loss = round(
                relationship.annual_flow_base * buyer_shock * config.pass_through_rate,
                6,
            )
            if revenue_loss <= 0.000001:
                continue
            losses_by_company[relationship.seller_company_id] += revenue_loss
            edge_pulses.append(
                EdgePulse(
                    relationship.relationship_id,
                    relationship.buyer_company_id,
                    relationship.seller_company_id,
                    round_index,
                    revenue_loss,
                )
            )
            seller = companies[relationship.seller_company_id]
            seller_loss_ratio = revenue_loss / seller.revenue if seller.revenue else 0.0
            next_shocks[relationship.seller_company_id] = max(
                next_shocks.get(relationship.seller_company_id, 0.0),
                seller_loss_ratio * config.propagation_factor,
            )
        active_shocks = next_shocks
        if not active_shocks:
            break
    return ScenarioResult(
        company_impacts={
            company_id: CompanyImpact(
                company_id,
                revenue_loss,
                revenue_loss * 0.5,
                company.operating_income - revenue_loss * 0.5,
                _stress_status(company, revenue_loss),
            )
            for company_id, company in companies.items()
            for revenue_loss in [losses_by_company[company_id]]
        },
        edge_pulses=edge_pulses,
    )
