from fragility_map.model.stress import (
    CompanyFinancials,
    NetworkRelationship,
    ScenarioConfig,
    run_cloud_spending_slowdown,
)


def test_direct_loss_ignores_confidence_score() -> None:
    companies = {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 100, 20, 10, 30, 1),
        "nvda": CompanyFinancials("nvda", "NVIDIA", "semiconductor", 50, 15, 5, 20, 1),
    }
    relationships = [NetworkRelationship("edge-1", "msft", "nvda", 10, 0.3, "inferred")]

    result = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(0.30, 0.80, 0.50, 2),
    )

    assert result.edge_pulses[0].revenue_loss == 2.4
    assert result.company_impacts["nvda"].revenue_loss == 2.4
    assert result.company_impacts["nvda"].stress_status == "exposed"


def test_critical_when_operating_income_turns_negative() -> None:
    companies = {
        "msft": CompanyFinancials("msft", "Microsoft", "cloud_platform", 100, 20, 10, 30, 1),
        "smci": CompanyFinancials("smci", "Supermicro", "infrastructure", 20, 2, 1, 1, 1),
    }
    relationships = [NetworkRelationship("edge-1", "msft", "smci", 10, 0.9, "percentage-derived")]

    result = run_cloud_spending_slowdown(
        companies,
        relationships,
        ScenarioConfig(0.40, 1.00, 0.50, 1),
    )

    assert result.company_impacts["smci"].stress_status == "critical"
