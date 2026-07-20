from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Scenario
from app.schemas import ScenarioIn, ScenarioOut, ScenarioRunOut
from app.services.scenarios import run_and_store

router = APIRouter()


@router.get("/scenarios", response_model=list[ScenarioOut])
def list_scenarios(session: Session = Depends(get_session)):
    return session.query(Scenario).all()


@router.post("/scenarios", response_model=ScenarioOut, status_code=201)
def create_scenario(payload: ScenarioIn, session: Session = Depends(get_session)):
    scenario = Scenario(
        name=payload.name,
        description=payload.description,
        shock_json={
            "origin_entity": payload.origin_entity,
            "kind": payload.kind,
            "magnitude": payload.magnitude,
            "unit": payload.unit,
        },
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    return scenario


@router.post("/scenarios/{scenario_id}/run", response_model=ScenarioRunOut)
def run_scenario_endpoint(scenario_id: str, session: Session = Depends(get_session)):
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    results, tot, run = run_and_store(session, scenario)
    return ScenarioRunOut(
        scenario_id=scenario.id,
        run_id=run.id,
        results=[r.model_dump() for r in results],
        totals=tot,
    )
