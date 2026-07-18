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
    run_compound_shock,
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


def _equity_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # relationship: ownership disclosed
        ProvenanceLabel.REPORTED,   # magnitude: loss stated in shock
        ProvenanceLabel.CALCULATED, # propagation: GAAP share is arithmetic
        ProvenanceLabel.CONSTRAINED,
    )


def test_equity_method_produces_solid_red_impact() -> None:
    rel = StructuralRelationship(
        "openai-msft",
        "openai",
        "msft",
        StructureType.EQUITY_METHOD,
        _equity_provenance(),
        ownership_share=0.27,
    )
    shock = Shock("openai", incremental_gaap_loss=10_000)

    result = run_compound_shock([rel], shock)

    edge = result.edges[0]
    assert edge.tier == Tier.SOLID_RED
    assert edge.result_kind == "impact"
    assert edge.value == -2_700.0
    node = result.nodes["msft"]
    assert node.quantified_impact == -2_700.0
    assert node.activated_exposure is None
    assert node.epistemic_state == "quantified_impact"


def test_equity_edge_skipped_when_no_gaap_loss() -> None:
    rel = StructuralRelationship(
        "openai-msft",
        "openai",
        "msft",
        StructureType.EQUITY_METHOD,
        _equity_provenance(),
        ownership_share=0.27,
    )
    shock = Shock("openai")

    result = run_compound_shock([rel], shock)

    assert result.edges == []
    assert "msft" not in result.nodes


def test_equity_method_accumulates_impacts_for_same_target() -> None:
    relationships = [
        StructuralRelationship(
            "openai-msft-primary",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _equity_provenance(),
            ownership_share=0.27,
        ),
        StructuralRelationship(
            "openai-msft-secondary",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _equity_provenance(),
            ownership_share=0.13,
        ),
    ]
    shock = Shock("openai", incremental_gaap_loss=10_000)

    result = run_compound_shock(relationships, shock)

    assert [edge.value for edge in result.edges] == [-2_700.0, -1_300.0]
    node = result.nodes["msft"]
    assert node.quantified_impact == -4_000.0
    assert node.activated_exposure is None
    assert node.epistemic_state == "quantified_impact"


def _take_or_pay_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # contract disclosed
        ProvenanceLabel.REPORTED,   # envelope amount disclosed
        ProvenanceLabel.CALCULATED, # envelope is a stated figure
        ProvenanceLabel.CONSTRAINED,
    )


def test_take_or_pay_produces_solid_orange_exposure_not_loss() -> None:
    rel = StructuralRelationship(
        "openai-coreweave",
        "openai",
        "coreweave",
        StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(),
        committed_envelope=11_900,
    )
    shock = Shock("openai", incremental_gaap_loss=10_000, credit_status="severe_distress")

    result = run_compound_shock([rel], shock)

    edge = result.edges[0]
    assert edge.tier == Tier.SOLID_ORANGE
    assert edge.result_kind == "exposure"
    assert edge.value == 11_900
    node = result.nodes["coreweave"]
    assert node.activated_exposure == 11_900
    assert node.quantified_impact is None
    assert node.epistemic_state == "exposure_detected"


def test_take_or_pay_stays_dormant_without_distress() -> None:
    rel = StructuralRelationship(
        "openai-coreweave",
        "openai",
        "coreweave",
        StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(),
        committed_envelope=11_900,
    )
    shock = Shock("openai", incremental_gaap_loss=10_000)  # credit_status defaults normal

    result = run_compound_shock([rel], shock)

    assert result.edges == []
    assert "coreweave" not in result.nodes
