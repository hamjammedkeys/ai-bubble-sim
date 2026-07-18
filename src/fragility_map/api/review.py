from dataclasses import dataclass, field

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fragility_map.extraction.candidates import RelationshipCandidateV2
from fragility_map.extraction.lifecycle import CandidateLifecycle
from fragility_map.extraction.proposers import KeywordProposer
from fragility_map.extraction.verifier import (
    SourceManifestEntry,
    VerificationResult,
    verify_candidate,
)

router = APIRouter(prefix="/api/extraction")


@dataclass
class ReviewSession:
    lifecycle: CandidateLifecycle = field(default_factory=CandidateLifecycle)
    filings: dict[str, str] = field(default_factory=dict)
    manifest: dict[str, SourceManifestEntry] = field(default_factory=dict)


SESSION = ReviewSession()


def reset_session() -> None:
    global SESSION
    SESSION = ReviewSession()


class ProposeRequest(BaseModel):
    source_id: str = Field(min_length=1)
    source_accession: str = Field(min_length=1)
    source_company_id: str = Field(min_length=1)
    target_company_id: str = Field(min_length=1)
    filing_text: str = Field(min_length=1)


def _verification_view(result: VerificationResult) -> dict:
    return {
        "checks": [
            {"name": c.name, "passed": c.passed, "detail": c.detail} for c in result.checks
        ],
        "mechanically_valid": result.mechanically_valid,
        "semantic_interpretation": result.semantic_interpretation,
    }


def _highlight(filing_text: str, candidate: RelationshipCandidateV2) -> dict | None:
    start = filing_text.find(candidate.quoted_text)
    if start < 0:
        return None
    return {"start": start, "end": start + len(candidate.quoted_text)}


@router.post("/propose")
def propose(request: ProposeRequest) -> dict:
    entry = SourceManifestEntry(request.source_accession, request.source_id)
    SESSION.filings[request.source_id] = request.filing_text
    SESSION.manifest[request.source_accession] = entry
    proposer = KeywordProposer(
        request.source_accession, request.source_company_id, request.target_company_id
    )
    views = []
    for candidate in proposer.propose(request.source_id, request.filing_text):
        result = verify_candidate(request.filing_text, candidate, [entry])
        SESSION.lifecycle.submit(candidate, result)
        views.append(
            {
                "candidate": candidate.model_dump(mode="json"),
                "verification": _verification_view(result),
                "highlight": _highlight(request.filing_text, candidate),
            }
        )
    return {"candidates": views}


class DecisionRequest(BaseModel):
    candidate_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


def _audit_view() -> list[dict]:
    return [
        {
            "candidate_id": e.candidate_id,
            "from_status": e.from_status.value if e.from_status else None,
            "to_status": e.to_status.value,
            "reviewer_id": e.reviewer_id,
            "reason": e.reason,
            "verification_valid": e.verification_valid,
        }
        for e in SESSION.lifecycle.audit_log()
    ]


def _decide(request: DecisionRequest, approve: bool) -> dict:
    try:
        if approve:
            candidate = SESSION.lifecycle.approve(
                request.candidate_id, request.reviewer_id, request.reason
            )
        else:
            candidate = SESSION.lifecycle.reject(
                request.candidate_id, request.reviewer_id, request.reason
            )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"candidate": candidate.model_dump(mode="json"), "audit": _audit_view()}


@router.post("/approve")
def approve(request: DecisionRequest) -> dict:
    return _decide(request, approve=True)


@router.post("/reject")
def reject(request: DecisionRequest) -> dict:
    return _decide(request, approve=False)
