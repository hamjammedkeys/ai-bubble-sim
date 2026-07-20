from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    entity_type: str | None = None
    aliases: list[str] | None = None


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_entity_id: str | None = None
    target_entity_id: str | None = None
    relationship_type: str
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    evidence_class: str
    permitted_operation: str | None = None
    unsupported_operation: str | None = None
    passage_id: str | None = None
    document_id: str | None = None
    status: str
    verification: dict | None = None
    created_at: datetime


class EdgeDetailOut(EdgeOut):
    """Edge plus its resolved citation, for the evidence inspector."""

    passage_text: str | None = None
    document_title: str | None = None
    document_url: str | None = None


class DocumentIn(BaseModel):
    title: str
    raw_text: str
    filing_type: str | None = None
    company: str | None = None
    url: str | None = None
    period: str | None = None


class DocumentFromUrlIn(BaseModel):
    url: str
    title: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    filing_type: str | None = None
    company: str | None = None
    period: str | None = None


class ExtractResponse(BaseModel):
    document_id: str
    candidates_created: int
    provider: str


class ReviewIn(BaseModel):
    reviewed_by: str | None = None


class EditEdgeIn(BaseModel):
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    relationship_type: str | None = None
    evidence_class: str | None = None
    permitted_operation: str | None = None
    unsupported_operation: str | None = None


class ScenarioIn(BaseModel):
    name: str
    origin_entity: str
    magnitude: float
    unit: str = "usd_billions"
    kind: str = "gaap_loss"
    description: str | None = None


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None = None
    description: str | None = None
    origin_entity: str | None = None


class ScenarioRunOut(BaseModel):
    scenario_id: str
    run_id: str
    results: list[dict]
    totals: dict


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    messages: list[ChatMessage]


class ChatOut(BaseModel):
    reply: str
    actions: list[dict]
