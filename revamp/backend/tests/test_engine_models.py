from app.engine.models import EdgeInput, EdgeResult, Shock


def test_shock_defaults():
    s = Shock(origin_entity="OpenAI", kind="gaap_loss", magnitude=10.0, unit="usd_billions")
    assert s.origin_entity == "OpenAI"
    assert s.magnitude == 10.0
    assert s.description is None


def test_edge_input_optional_value():
    e = EdgeInput(
        id="e1",
        source_entity="Nvidia",
        target_entity="CoreWeave",
        relationship_type="supplier_dependency",
        evidence_class="unknown",
    )
    assert e.value is None


def test_edge_result_carries_kind_and_visual():
    r = EdgeResult(
        edge_id="e1",
        source_entity="Microsoft",
        target_entity="OpenAI",
        relationship_type="equity_method",
        kind="impact",
        value=2.7,
        unit="usd_billions",
        label="$2.7B indicative equity-method impact",
        caveat="accounting basis",
        realized_loss=None,
        evidence_class="calculated",
        visual_state="solid_red",
    )
    assert r.kind == "impact"
    assert r.realized_loss is None
    assert r.visual_state == "solid_red"
