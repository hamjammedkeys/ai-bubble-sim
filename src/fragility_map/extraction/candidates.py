from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class CandidateStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class RelationshipCandidateV2(BaseModel):
    candidate_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_accession: str = Field(min_length=1)
    source_company_id: str = Field(min_length=1)
    target_company_id: str | None = None
    relationship_type: str = Field(min_length=1)
    quoted_text: str = Field(min_length=1)
    numeric_token: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    supported_rule: str = Field(min_length=1)
    unsupported_inference: str = Field(min_length=1)
    status: CandidateStatus = CandidateStatus.PROPOSED


class RelationshipProposer(Protocol):
    def propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]: ...


def propose_candidates(
    proposer: RelationshipProposer, source_id: str, filing_text: str
) -> list[RelationshipCandidateV2]:
    return proposer.propose(source_id, filing_text)
