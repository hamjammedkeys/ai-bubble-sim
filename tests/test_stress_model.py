from fragility_map.model.evidence import (
    EdgeProvenance,
    ProvenanceLabel,
    StructureType,
    Tier,
    quantifies_propagation,
)
from fragility_map.model.propagation import (
    Shock,
    StructuralRelationship,
)
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


def test_quantifies_propagation_requires_reported_or_calculated() -> None:
    reported = EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.REPORTED,
    )
    assumed = EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CONSTRAINED,
        ProvenanceLabel.ASSUMED,
        ProvenanceLabel.ASSUMED,
    )
    assert quantifies_propagation(reported) is True
    assert quantifies_propagation(assumed) is False


def test_tier_values_are_the_four_canonical_strings() -> None:
    assert {t.value for t in Tier} == {
        "solid_red",
        "solid_orange",
        "dashed_amber",
        "diffuse_amber",
    }


def test_shock_defaults_are_normal_and_not_defaulted() -> None:
    shock = Shock("openai", incremental_gaap_loss=10_000)
    assert shock.credit_status == "normal"
    assert shock.default_status == "not_defaulted"


def test_structural_relationship_holds_only_disclosed_parameters() -> None:
    rel = StructuralRelationship(
        "openai-msft",
        "openai",
        "msft",
        StructureType.EQUITY_METHOD,
        _reported_provenance(),
        ownership_share=0.27,
        source_accession="msft-10k-2025",
    )
    assert rel.ownership_share == 0.27
    assert rel.concentration is None
    assert rel.committed_envelope is None


def _reported_provenance():
    from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel

    return EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.REPORTED,
    )
