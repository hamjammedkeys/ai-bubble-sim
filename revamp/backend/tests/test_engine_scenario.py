from app.engine.models import EdgeInput, Shock
from app.engine.scenario import edge_touches_shock, run_scenario, totals

SHOCK = Shock(origin_entity="OpenAI", kind="gaap_loss", magnitude=10.0, unit="usd_billions")


def _edges() -> list[EdgeInput]:
    return [
        EdgeInput(id="msft", source_entity="Microsoft", target_entity="OpenAI",
                  relationship_type="equity_method", metric="ownership_pct", value=27.0,
                  unit="percent", evidence_class="reported"),
        EdgeInput(id="cw", source_entity="OpenAI", target_entity="CoreWeave",
                  relationship_type="purchase_obligation", metric="contract_value", value=11.9,
                  unit="usd_billions", evidence_class="reported"),
        EdgeInput(id="nv", source_entity="CoreWeave", target_entity="Nvidia",
                  relationship_type="supplier_dependency", value=None, evidence_class="unknown"),
        EdgeInput(id="asml", source_entity="TSMC", target_entity="ASML",
                  relationship_type="supplier_dependency", value=None, evidence_class="unknown"),
    ]


def test_touch_detection():
    edges = _edges()
    assert edge_touches_shock(edges[0], SHOCK) is True   # MSFT->OpenAI
    assert edge_touches_shock(edges[1], SHOCK) is True   # OpenAI->CoreWeave
    assert edge_touches_shock(edges[3], SHOCK) is False  # TSMC->ASML untouched


def test_hero_scenario_produces_impact_and_exposure_separately():
    results = run_scenario(SHOCK, _edges())
    by_id = {r.edge_id: r for r in results}

    # untouched TSMC->ASML edge is not in the results
    assert "asml" not in by_id

    assert by_id["msft"].kind == "impact"
    assert round(by_id["msft"].value, 2) == 2.7
    assert by_id["msft"].visual_state == "solid_red"

    assert by_id["cw"].kind == "exposure"
    assert by_id["cw"].value == 11.9
    assert by_id["cw"].realized_loss is None
    assert by_id["cw"].visual_state == "solid_orange"

    assert by_id["nv"].kind == "unresolved"
    assert by_id["nv"].visual_state == "dashed_amber"


def test_totals_never_conflate_impact_and_exposure():
    t = totals(run_scenario(SHOCK, _edges()))
    assert round(t["impact_total"], 2) == 2.7      # only the equity-method impact
    assert t["exposure_total"] == 11.9             # only the disclosed exposure
    assert t["impact_total"] != t["exposure_total"]
    assert t["unresolved_count"] == 1


def test_result_is_independent_of_edge_order():
    # The 2-hop behavioural edge (CoreWeave->Nvidia) must be reached regardless of
    # where it sits in the input list: reachability is a fixpoint, not a single pass.
    import itertools

    base = _edges()
    for perm in itertools.permutations(base):
        by_id = {r.edge_id: r for r in run_scenario(SHOCK, list(perm))}
        assert set(by_id) == {"msft", "cw", "nv"}          # asml never reachable
        assert round(by_id["msft"].value, 2) == 2.7
        assert by_id["cw"].value == 11.9
        assert by_id["nv"].kind == "unresolved"


def test_disconnected_edge_stays_untouched_even_multi_hop():
    # An edge reachable only through an entity that itself is never reached
    # must not appear. ASML is connected to TSMC only; TSMC is never reached.
    results = run_scenario(SHOCK, _edges())
    assert "asml" not in {r.edge_id for r in results}


def test_multi_hop_exposure_is_not_summed_into_headline_total():
    # A structural exposure edge that the shock does NOT touch directly (only
    # reachable multi-hop via CoreWeave) must render as the amber dissolve and
    # NEVER inflate exposure_total. This locks the credibility-critical rule:
    # a headline total only aggregates exposures the shock touches directly.
    edges = _edges() + [
        EdgeInput(id="oracle", source_entity="CoreWeave", target_entity="Oracle",
                  relationship_type="purchase_obligation", metric="contract_value",
                  value=50.0, unit="usd_billions", evidence_class="reported"),
    ]
    results = run_scenario(SHOCK, edges)
    by_id = {r.edge_id: r for r in results}

    assert "oracle" in by_id                       # reachable, so it shows...
    assert by_id["oracle"].kind == "unresolved"    # ...but as the amber dissolve
    assert by_id["oracle"].visual_state == "dashed_amber"

    t = totals(results)
    assert t["exposure_total"] == 11.9             # NOT 61.9 — the $50B is not summed


def test_empty_origin_shock_produces_no_results():
    from app.engine.models import Shock as _Shock

    assert run_scenario(_Shock(origin_entity="", kind="gaap_loss", magnitude=10.0), _edges()) == []
