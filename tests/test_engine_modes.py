from fragility_map.api.v2_payload import build_evidence_payload
from fragility_map.model.evidence import Tier
from fragility_map.model.propagation import run_compound_shock, run_sensitivity
from fragility_map.seed.hero import hero_companies, hero_relationships, hero_shock


def test_realized_loss_is_dashed_amber_without_point_value() -> None:
    result = run_compound_shock(
        hero_relationships(), hero_shock(), include_realized_loss_guardrail=True
    )

    edge = next(
        edge
        for edge in result.edges
        if edge.relationship_id == "openai-coreweave-realized-loss"
    )

    assert edge.tier is Tier.DASHED_AMBER
    assert edge.result_kind == "realized_loss_unidentifiable"
    assert edge.value is None


def test_sensitivity_reports_missing_credit_parameters_without_fabricating_range() -> None:
    sensitivity = run_sensitivity(hero_relationships(), hero_shock(), ("PD", "LGD", "timing"))

    assert [row.parameter for row in sensitivity.rows] == ["PD", "LGD", "timing"]
    assert all(
        row.supported_range is None and row.output_status == "not_identifiable"
        for row in sensitivity.rows
    )


def test_payload_only_serializes_realized_loss_guardrail_when_requested() -> None:
    relationships = hero_relationships()
    result = run_compound_shock(
        relationships, hero_shock(), include_realized_loss_guardrail=True
    )

    default_payload = build_evidence_payload(hero_companies(), relationships, result)
    guardrail_payload = build_evidence_payload(
        hero_companies(),
        relationships,
        result,
        include_realized_loss_guardrail=True,
    )

    assert all(edge["tier"] != Tier.DASHED_AMBER.value for edge in default_payload["edges"])
    assert any(
        edge["relationshipId"] == "openai-coreweave-realized-loss"
        and edge["tier"] == Tier.DASHED_AMBER.value
        and edge["value"] is None
        for edge in guardrail_payload["edges"]
    )
