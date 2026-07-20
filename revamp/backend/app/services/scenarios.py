from sqlalchemy.orm import Session

from app.engine.models import EdgeInput, EdgeResult, Shock
from app.engine.scenario import run_scenario, totals
from app.models import Edge, Entity, Scenario, ScenarioRun


def edges_to_inputs(session: Session) -> list[EdgeInput]:
    inputs: list[EdgeInput] = []
    approved = session.query(Edge).filter(Edge.status == "approved").all()
    for edge in approved:
        src = session.get(Entity, edge.source_entity_id) if edge.source_entity_id else None
        tgt = session.get(Entity, edge.target_entity_id) if edge.target_entity_id else None
        if src is None or tgt is None:
            # An edge with an unresolved endpoint cannot participate honestly:
            # an empty entity name could otherwise match a malformed empty shock
            # origin. Skip it rather than feed a "" entity into the engine.
            continue
        inputs.append(
            EdgeInput(
                id=edge.id,
                source_entity=src.name if src else "",
                target_entity=tgt.name if tgt else "",
                relationship_type=edge.relationship_type,
                metric=edge.metric,
                value=edge.value,
                unit=edge.unit,
                period=edge.period,
                evidence_class=edge.evidence_class,
            )
        )
    return inputs


def shock_from_scenario(scenario: Scenario) -> Shock:
    data = scenario.shock_json or {}
    return Shock(
        origin_entity=data.get("origin_entity", ""),
        kind=data.get("kind", "shock"),
        magnitude=data.get("magnitude"),
        unit=data.get("unit"),
        description=data.get("description"),
    )


def run_and_store(session: Session, scenario: Scenario) -> tuple[list[EdgeResult], dict, ScenarioRun]:
    shock = shock_from_scenario(scenario)
    results = run_scenario(shock, edges_to_inputs(session))
    tot = totals(results)
    run = ScenarioRun(
        scenario_id=scenario.id,
        results={"results": [r.model_dump() for r in results], "totals": tot},
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return results, tot, run
