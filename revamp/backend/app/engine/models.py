from pydantic import BaseModel


class Shock(BaseModel):
    origin_entity: str
    kind: str
    magnitude: float | None = None
    unit: str | None = None
    description: str | None = None


class EdgeInput(BaseModel):
    id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    evidence_class: str


class EdgeResult(BaseModel):
    edge_id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    kind: str  # "impact" | "exposure" | "unresolved"
    value: float | None
    unit: str | None
    label: str
    caveat: str
    realized_loss: float | None
    evidence_class: str
    visual_state: str  # "solid_red" | "solid_orange" | "dashed_amber"
