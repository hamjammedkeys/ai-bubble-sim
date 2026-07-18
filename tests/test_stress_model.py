from fragility_map.model.evidence import (
    EdgeProvenance,
    ProvenanceLabel,
    StructureType,
    Tier,
    quantifies_propagation,
)
from fragility_map.model.propagation import (
    EdgeFlowShock,
    NodeResult,
    Shock,
    ShockResult,
    StructuralRelationship,
    rank_vulnerability,
    run_compound_shock,
    run_edge_flow_shock,
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


def test_take_or_pay_activates_on_default_and_uses_required_basis() -> None:
    rel = StructuralRelationship(
        "openai-coreweave",
        "openai",
        "coreweave",
        StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(),
        committed_envelope=11_900,
    )

    result = run_compound_shock([rel], Shock("openai", default_status="defaulted"))

    assert result.edges[0].basis == (
        "take-or-pay contract envelope activated (not a realized loss)"
    )
    assert result.nodes["coreweave"].activated_exposure == 11_900


def test_take_or_pay_accumulates_while_preserving_quantified_impact() -> None:
    relationships = [
        StructuralRelationship(
            "openai-msft-equity",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _equity_provenance(),
            ownership_share=0.25,
        ),
        StructuralRelationship(
            "openai-msft-contract-1",
            "openai",
            "msft",
            StructureType.TAKE_OR_PAY,
            _take_or_pay_provenance(),
            committed_envelope=100,
        ),
        StructuralRelationship(
            "openai-msft-contract-2",
            "openai",
            "msft",
            StructureType.TAKE_OR_PAY,
            _take_or_pay_provenance(),
            committed_envelope=50,
        ),
    ]

    result = run_compound_shock(
        relationships,
        Shock("openai", incremental_gaap_loss=400, credit_status="severe_distress"),
    )

    node = result.nodes["msft"]
    assert node.quantified_impact == -100
    assert node.activated_exposure == 150
    assert node.epistemic_state == "quantified_impact"


def test_take_or_pay_dissolves_non_quantifying_and_rejects_missing_envelope() -> None:
    non_quantifying = EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.ASSUMED,
        ProvenanceLabel.CONSTRAINED,
    )
    relationships = [
        StructuralRelationship(
            "openai-coreweave-assumed",
            "openai",
            "coreweave",
            StructureType.TAKE_OR_PAY,
            non_quantifying,
            committed_envelope=11_900,
        ),
        StructuralRelationship(
            "openai-coreweave-missing",
            "openai",
            "coreweave",
            StructureType.TAKE_OR_PAY,
            _take_or_pay_provenance(),
        ),
    ]

    result = run_compound_shock(
        relationships,
        Shock("openai", credit_status="severe_distress"),
    )

    assert len(result.edges) == 1
    assert result.edges[0].relationship_id == "openai-coreweave-assumed"
    assert result.edges[0].tier == Tier.DIFFUSE_AMBER
    assert result.edges[0].value is None
    assert result.nodes["coreweave"].epistemic_state == "not_identifiable"


def _behavioural_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # relationship exists (disclosed dependency)
        ProvenanceLabel.ASSUMED,
        ProvenanceLabel.ASSUMED,    # propagation NOT constrained
        ProvenanceLabel.ASSUMED,
    )


def test_behavioural_edge_dissolves_to_diffuse_amber_without_number() -> None:
    rel = StructuralRelationship(
        "coreweave-nvda",
        "coreweave",
        "nvda",
        StructureType.BEHAVIOURAL,
        _behavioural_provenance(),
    )
    shock = Shock("coreweave", incremental_gaap_loss=5_000, credit_status="severe_distress")

    result = run_compound_shock([rel], shock)

    edge = result.edges[0]
    assert edge.tier == Tier.DIFFUSE_AMBER
    assert edge.result_kind == "behavioural"
    assert edge.value is None
    node = result.nodes["nvda"]
    assert node.quantified_impact is None
    assert node.activated_exposure is None
    assert node.epistemic_state == "not_identifiable"


def test_unconstrained_structural_edge_dissolves_without_overwriting_impact() -> None:
    relationships = [
        StructuralRelationship(
            "openai-msft-quantified",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _equity_provenance(),
            ownership_share=0.25,
        ),
        StructuralRelationship(
            "openai-msft-unconstrained",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _behavioural_provenance(),
            ownership_share=0.10,
        ),
    ]

    result = run_compound_shock(
        relationships,
        Shock("openai", incremental_gaap_loss=400),
    )

    assert result.edges[1].tier == Tier.DIFFUSE_AMBER
    assert result.edges[1].result_kind == "behavioural"
    assert result.edges[1].value is None
    assert result.nodes["msft"].quantified_impact == -100
    assert result.nodes["msft"].epistemic_state == "quantified_impact"


def _concentration_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.CONSTRAINED,
    )


def test_concentration_edge_is_solid_only_under_edge_flow_shock() -> None:
    rel = StructuralRelationship(
        "msft-coreweave",
        "msft",
        "coreweave",
        StructureType.CUSTOMER_CONCENTRATION,
        _concentration_provenance(),
        concentration=0.62,
    )

    result = run_edge_flow_shock(
        [rel], EdgeFlowShock("msft-coreweave", flow_change=-0.2000009)
    )

    edge = result.edges[0]
    assert edge.tier == Tier.SOLID_ORANGE
    assert edge.result_kind == "exposure"
    assert edge.value == -0.124001
    assert result.nodes["coreweave"].activated_exposure == -0.124001


def test_aggregate_shock_never_produces_a_concentration_result() -> None:
    relationships = [
        StructuralRelationship(
            "msft-coreweave-quantified",
            "msft",
            "coreweave",
            StructureType.CUSTOMER_CONCENTRATION,
            _concentration_provenance(),
            concentration=0.62,
        ),
        StructuralRelationship(
            "msft-coreweave-unconstrained",
            "msft",
            "coreweave",
            StructureType.CUSTOMER_CONCENTRATION,
            _behavioural_provenance(),
            concentration=0.62,
        ),
    ]

    result = run_compound_shock(
        relationships, Shock("msft", incremental_gaap_loss=10_000)
    )

    assert result.edges == []
    assert result.nodes == {}


def test_edge_flow_shock_only_quantifies_its_named_concentration_edge() -> None:
    relationships = [
        StructuralRelationship(
            "other-concentration",
            "msft",
            "other",
            StructureType.CUSTOMER_CONCENTRATION,
            _concentration_provenance(),
            concentration=0.5,
        ),
        StructuralRelationship(
            "named-equity",
            "msft",
            "coreweave",
            StructureType.EQUITY_METHOD,
            _concentration_provenance(),
            concentration=0.62,
        ),
    ]

    result = run_edge_flow_shock(
        relationships, EdgeFlowShock("named-equity", flow_change=-0.20)
    )

    assert result.edges == []
    assert result.nodes == {}


def test_edge_flow_shock_rejects_missing_or_non_quantifying_concentration() -> None:
    relationships = [
        StructuralRelationship(
            "missing",
            "msft",
            "coreweave",
            StructureType.CUSTOMER_CONCENTRATION,
            _concentration_provenance(),
        ),
        StructuralRelationship(
            "unconstrained",
            "msft",
            "coreweave",
            StructureType.CUSTOMER_CONCENTRATION,
            _behavioural_provenance(),
            concentration=0.62,
        ),
    ]

    for relationship_id in ("missing", "unconstrained"):
        result = run_edge_flow_shock(
            relationships, EdgeFlowShock(relationship_id, flow_change=-0.20)
        )
        assert result.edges == []
        assert result.nodes == {}


def test_ranking_excludes_exposure_and_unidentifiable_nodes() -> None:
    result = ShockResult(
        edges=[],
        nodes={
            "msft": NodeResult("msft", quantified_impact=-2_700.0, activated_exposure=None,
                               epistemic_state="quantified_impact"),
            "coreweave": NodeResult("coreweave", quantified_impact=None,
                                    activated_exposure=11_900, epistemic_state="exposure_detected"),
            "nvda": NodeResult("nvda", quantified_impact=None, activated_exposure=None,
                               epistemic_state="not_identifiable"),
        },
    )

    ranking = rank_vulnerability(result)

    assert ranking == [("msft", 2_700.0)]


def test_ranking_sorts_absolute_magnitudes_and_includes_zero() -> None:
    result = ShockResult(
        edges=[],
        nodes={
            "zero": NodeResult("zero", 0.0, None, "quantified_impact"),
            "gain": NodeResult("gain", 12.0, None, "quantified_impact"),
            "loss": NodeResult("loss", -30.0, None, "quantified_impact"),
        },
    )

    assert rank_vulnerability(result) == [
        ("loss", 30.0),
        ("gain", 12.0),
        ("zero", 0.0),
    ]


def test_ranking_excludes_numeric_impacts_without_quantified_state() -> None:
    result = ShockResult(
        edges=[],
        nodes={
            "exposure": NodeResult("exposure", -50.0, 100.0, "exposure_detected"),
            "unknown": NodeResult("unknown", 40.0, None, "not_identifiable"),
            "unaffected": NodeResult("unaffected", 0.0, None, "unaffected"),
        },
    )

    assert rank_vulnerability(result) == []


def test_hero_compound_credit_event_lights_impact_and_exposure() -> None:
    equity = StructuralRelationship(
        "openai-msft", "openai", "msft", StructureType.EQUITY_METHOD,
        _equity_provenance(), ownership_share=0.27,
    )
    take_or_pay = StructuralRelationship(
        "openai-coreweave", "openai", "coreweave", StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(), committed_envelope=11_900,
    )
    downstream = StructuralRelationship(
        "coreweave-nvda", "openai", "nvda", StructureType.BEHAVIOURAL,
        _behavioural_provenance(),
    )
    shock = Shock("openai", incremental_gaap_loss=10_000, credit_status="severe_distress")

    result = run_compound_shock([equity, take_or_pay, downstream], shock)

    assert result.nodes["msft"].epistemic_state == "quantified_impact"
    assert result.nodes["msft"].quantified_impact == -2_700.0
    assert result.nodes["coreweave"].epistemic_state == "exposure_detected"
    assert result.nodes["coreweave"].activated_exposure == 11_900
    assert result.nodes["nvda"].epistemic_state == "not_identifiable"
    tiers = {e.relationship_id: e.tier for e in result.edges}
    assert tiers["openai-msft"] == Tier.SOLID_RED
    assert tiers["openai-coreweave"] == Tier.SOLID_ORANGE
    assert tiers["coreweave-nvda"] == Tier.DIFFUSE_AMBER
