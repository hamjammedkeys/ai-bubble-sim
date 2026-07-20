from typing import Literal

from pydantic import BaseModel

RelationshipType = Literal[
    "investment_exposure",
    "equity_method",
    "customer_concentration",
    "purchase_obligation",
    "take_or_pay",
    "counterparty_credit_exposure",
    "commercial_spending",
    "operational_dependency",
    "behavioural_response",
    "supplier_dependency",
]

EvidenceClass = Literal[
    "reported",
    "calculated",
    "constrained",
    "assumed",
    "unknown",
]


class CandidateEdge(BaseModel):
    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    metric: str
    value: float | None
    unit: str | None
    period: str | None
    exact_passage: str
    document_id: str
    permitted_operation: str
    unsupported_operation: str
    missing_information: list[str]
    evidence_class: EvidenceClass
    confidence_note: str


class ExtractionResult(BaseModel):
    candidates: list[CandidateEdge]
