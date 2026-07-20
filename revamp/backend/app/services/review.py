from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.extraction.schema import CandidateEdge
from app.models import Document, Edge, Entity, Passage
from app.verification import verify_candidate

EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "metric",
        "value",
        "unit",
        "period",
        "relationship_type",
        "evidence_class",
        "permitted_operation",
        "unsupported_operation",
    }
)


class InvalidTransition(ValueError):
    """Raised when an edge is not in a state that permits the requested transition."""


def _get_edge(session: Session, edge_id: str) -> Edge:
    edge = session.get(Edge, edge_id)
    if edge is None:
        raise KeyError(edge_id)
    return edge


def _require_candidate(edge: Edge) -> None:
    if edge.status != "candidate":
        raise InvalidTransition(f"edge {edge.id} is '{edge.status}', not 'candidate'")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def approve_edge(session: Session, edge_id: str, reviewed_by: str | None = None) -> Edge:
    edge = _get_edge(session, edge_id)
    _require_candidate(edge)
    edge.status = "approved"
    edge.reviewed_by = reviewed_by
    edge.reviewed_at = _now()
    session.commit()
    session.refresh(edge)
    return edge


def reject_edge(session: Session, edge_id: str, reviewed_by: str | None = None) -> Edge:
    edge = _get_edge(session, edge_id)
    _require_candidate(edge)
    edge.status = "rejected"
    edge.reviewed_by = reviewed_by
    edge.reviewed_at = _now()
    session.commit()
    session.refresh(edge)
    return edge


def _rebuild_candidate(edge: Edge, source_name: str, target_name: str, passage_text: str) -> CandidateEdge:
    return CandidateEdge(
        source_entity=source_name,
        target_entity=target_name,
        relationship_type=edge.relationship_type,
        metric=edge.metric or "",
        value=edge.value,
        unit=edge.unit,
        period=edge.period,
        exact_passage=passage_text,
        document_id=edge.document_id or "",
        permitted_operation=edge.permitted_operation or "",
        unsupported_operation=edge.unsupported_operation or "",
        missing_information=[],
        evidence_class=edge.evidence_class,
        confidence_note="",
    )


def edit_edge(session: Session, edge_id: str, updates: dict) -> Edge:
    edge = _get_edge(session, edge_id)
    _require_candidate(edge)
    for field, value in updates.items():
        if field in EDITABLE_FIELDS:
            setattr(edge, field, value)
    session.flush()

    src = session.get(Entity, edge.source_entity_id) if edge.source_entity_id else None
    tgt = session.get(Entity, edge.target_entity_id) if edge.target_entity_id else None
    psg = session.get(Passage, edge.passage_id) if edge.passage_id else None
    document = session.get(Document, edge.document_id) if edge.document_id else None

    edge.verification = verify_candidate(
        _rebuild_candidate(
            edge,
            source_name=src.name if src else "",
            target_name=tgt.name if tgt else "",
            passage_text=psg.text if psg else "",
        ),
        document.raw_text if document else "",
        document_exists=document is not None,
    )
    edge.status = "candidate"
    session.commit()
    session.refresh(edge)
    return edge
