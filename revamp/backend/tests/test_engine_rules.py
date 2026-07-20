from app.engine.models import EdgeInput, Shock
from app.engine.rules import (
    BEHAVIOURAL_TYPES,
    STRUCTURAL_RULES,
    equity_method_rule,
    exposure_rule,
    unresolved_result,
)

SHOCK = Shock(origin_entity="OpenAI", kind="gaap_loss", magnitude=10.0, unit="usd_billions")


def _edge(**over) -> EdgeInput:
    base = dict(
        id="e1",
        source_entity="Microsoft",
        target_entity="OpenAI",
        relationship_type="equity_method",
        metric="ownership_pct",
        value=27.0,
        unit="percent",
        period="FY2026",
        evidence_class="reported",
    )
    base.update(over)
    return EdgeInput(**base)


def test_equity_method_computes_2_7B_impact():
    r = equity_method_rule(_edge(), SHOCK)
    assert r.kind == "impact"
    assert round(r.value, 2) == 2.7          # 10 * 0.27
    assert r.realized_loss is None
    assert r.visual_state == "solid_red"


def test_exposure_surfaces_ceiling_not_loss():
    edge = _edge(
        source_entity="OpenAI",
        target_entity="CoreWeave",
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
    )
    r = exposure_rule(edge, SHOCK)
    assert r.kind == "exposure"
    assert r.value == 11.9                    # disclosed ceiling, surfaced as-is
    assert r.realized_loss is None            # NEVER a realized loss
    assert r.visual_state == "solid_orange"
    assert "PD" in r.caveat or "realized" in r.caveat.lower()


def test_exposure_is_never_an_impact():
    edge = _edge(relationship_type="take_or_pay", source_entity="OpenAI", target_entity="Oracle", value=30.0)
    r = exposure_rule(edge, SHOCK)
    assert r.kind != "impact"
    assert r.realized_loss is None


def test_behavioural_edge_is_unresolved():
    edge = _edge(relationship_type="supplier_dependency", source_entity="CoreWeave", target_entity="Nvidia", value=None, evidence_class="unknown")
    r = unresolved_result(edge)
    assert r.kind == "unresolved"
    assert r.value is None
    assert r.visual_state == "dashed_amber"


def test_registries_partition_the_types():
    assert "equity_method" in STRUCTURAL_RULES
    assert "purchase_obligation" in STRUCTURAL_RULES
    assert "supplier_dependency" in BEHAVIOURAL_TYPES
    assert set(STRUCTURAL_RULES).isdisjoint(BEHAVIOURAL_TYPES)


def test_ownership_fraction_handles_already_fractional():
    # a value <= 1 with no percent unit is treated as an already-fractional ownership
    edge = _edge(value=0.27, unit=None)
    r = equity_method_rule(edge, SHOCK)
    assert round(r.value, 2) == 2.7


def test_exposure_label_suffix_follows_unit_not_hardcoded_billions():
    # a usd_millions exposure must not be mislabelled with a 'B' (1000x error)
    edge = _edge(relationship_type="purchase_obligation", source_entity="OpenAI",
                 target_entity="CoreWeave", metric="contract_value", value=500.0, unit="usd_millions")
    r = exposure_rule(edge, SHOCK)
    assert "500.0M" in r.label
    assert "B" not in r.label
    assert r.value == 500.0 and r.unit == "usd_millions"
