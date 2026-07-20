from app.engine.models import EdgeInput, EdgeResult, Shock
from app.engine.rules import BEHAVIOURAL_TYPES, STRUCTURAL_RULES, unresolved_result


def edge_touches_shock(edge: EdgeInput, shock: Shock) -> bool:
    return shock.origin_entity in (edge.source_entity, edge.target_entity)


def _affected_entities(shock: Shock, edges: list[EdgeInput]) -> set[str]:
    """Entities reachable from the shock origin by undirected edge connectivity.

    Computed to a fixpoint so the result is independent of edge ordering. The
    ripple travels through every edge type (structural and behavioural alike);
    how far it reaches is a graph fact, while whether each reached edge renders
    as a quantified impact/exposure or an amber dissolve is decided per edge by
    its relationship_type in run_scenario (ADR 0003/0004).
    """
    affected = {shock.origin_entity}
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge.source_entity in affected or edge.target_entity in affected:
                for name in (edge.source_entity, edge.target_entity):
                    if name not in affected:
                        affected.add(name)
                        changed = True
    return affected


def run_scenario(shock: Shock, edges: list[EdgeInput]) -> list[EdgeResult]:
    """Quantify only the structural edges the shock touches *directly*; render
    every other reachable edge as the amber dissolve.

    A number (impact/exposure) is produced ONLY for a structural edge incident
    to the shock origin — so a headline total can never absorb an exposure that
    is merely somewhere in the same connected component. Everything else the
    ripple reaches (behavioural edges, and structural edges only reachable via a
    behavioural/multi-hop path) renders `unresolved`/`dashed_amber`: documented
    reach, no invented number (ADR 0003/0004). Unreachable edges are omitted.
    """
    if not shock.origin_entity:
        return []
    affected = _affected_entities(shock, edges)
    results: list[EdgeResult] = []
    for edge in edges:
        if edge.source_entity not in affected and edge.target_entity not in affected:
            continue
        if edge_touches_shock(edge, shock) and edge.relationship_type in STRUCTURAL_RULES:
            results.append(STRUCTURAL_RULES[edge.relationship_type](edge, shock))
        else:
            results.append(unresolved_result(edge))
    return results


def totals(results: list[EdgeResult]) -> dict:
    impact_total = sum(r.value or 0.0 for r in results if r.kind == "impact")
    exposure_total = sum(r.value or 0.0 for r in results if r.kind == "exposure")
    unresolved_count = sum(1 for r in results if r.kind == "unresolved")
    return {
        "impact_total": impact_total,
        "exposure_total": exposure_total,
        "unresolved_count": unresolved_count,
    }
