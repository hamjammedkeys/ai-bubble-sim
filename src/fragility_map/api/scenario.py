from fastapi import APIRouter
from pydantic import BaseModel, Field

from fragility_map.api import review
from fragility_map.extraction.candidates import CandidateStatus
from fragility_map.extraction.lifecycle import promote_approved
from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, StructureType
from fragility_map.model.propagation import (
    Shock,
    ShockResult,
    StructuralRelationship,
    run_compound_shock,
)

router = APIRouter(prefix="/api/scenario")

_QUANTIFYING = EdgeProvenance(
    ProvenanceLabel.REPORTED,
    ProvenanceLabel.REPORTED,
    ProvenanceLabel.CALCULATED,
    ProvenanceLabel.CONSTRAINED,
)
_BEHAVIOURAL = EdgeProvenance(
    ProvenanceLabel.REPORTED,
    ProvenanceLabel.ASSUMED,
    ProvenanceLabel.ASSUMED,
    ProvenanceLabel.ASSUMED,
)


def seed_hero_relationships() -> list[StructuralRelationship]:
    """The hero triangle minus the take-or-pay edge, which only exists once a
    human approves the uploaded candidate. Money is actual USD to match the
    verifier/candidate convention used by promoted edges."""
    return [
        StructuralRelationship(
            "openai-msft-equity",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _QUANTIFYING,
            ownership_share=0.27,
        ),
        StructuralRelationship(
            "coreweave-nvda-behavioural",
            "openai",
            "nvda",
            StructureType.BEHAVIOURAL,
            _BEHAVIOURAL,
        ),
    ]


def _promoted() -> list[StructuralRelationship]:
    promoted: list[StructuralRelationship] = []
    items = review.SESSION.lifecycle._items  # noqa: SLF001
    for candidate_id in list(items):
        candidate, verification = items[candidate_id]
        if candidate.status in {CandidateStatus.APPROVED, CandidateStatus.EDITED}:
            promoted.append(promote_approved(candidate, verification))
    return promoted


class CreditEventRequest(BaseModel):
    source_company_id: str = Field(default="openai", min_length=1)
    incremental_gaap_loss: float = Field(default=10_000_000_000)
    credit_status: str = Field(default="severe_distress", min_length=1)


def _serialize(result: ShockResult) -> dict:
    return {
        "edges": [
            {
                "relationship_id": e.relationship_id,
                "source": e.source_company_id,
                "target": e.target_company_id,
                "tier": e.tier.value,
                "result_kind": e.result_kind,
                "value": e.value,
                "basis": e.basis,
            }
            for e in result.edges
        ],
        "nodes": {
            company_id: {
                "quantified_impact": node.quantified_impact,
                "activated_exposure": node.activated_exposure,
                "epistemic_state": node.epistemic_state,
            }
            for company_id, node in result.nodes.items()
        },
    }


@router.post("/credit-event")
def credit_event(request: CreditEventRequest) -> dict:
    relationships = seed_hero_relationships() + _promoted()
    shock = Shock(
        request.source_company_id,
        incremental_gaap_loss=request.incremental_gaap_loss,
        credit_status=request.credit_status,
    )
    return _serialize(run_compound_shock(relationships, shock))
