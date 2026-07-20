from sqlalchemy.orm import Session

from app.extraction.schema import ExtractionResult
from app.models import Document, Edge, Entity, Passage
from app.verification import verify_candidate


def get_or_create_entity(session: Session, name: str) -> Entity:
    entity = session.query(Entity).filter_by(name=name).one_or_none()
    if entity is None:
        entity = Entity(name=name, aliases=[])
        session.add(entity)
        session.flush()
    return entity


def persist_candidates(session: Session, result: ExtractionResult, document: Document) -> list[Edge]:
    created: list[Edge] = []
    for candidate in result.candidates:
        source = get_or_create_entity(session, candidate.source_entity)
        target = get_or_create_entity(session, candidate.target_entity)

        passage = Passage(document_id=document.id, text=candidate.exact_passage)
        session.add(passage)
        session.flush()

        verification = verify_candidate(candidate, document.raw_text, document_exists=True)
        edge = Edge(
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type=candidate.relationship_type,
            metric=candidate.metric,
            value=candidate.value,
            unit=candidate.unit,
            period=candidate.period,
            evidence_class=candidate.evidence_class,
            permitted_operation=candidate.permitted_operation,
            unsupported_operation=candidate.unsupported_operation,
            passage_id=passage.id,
            document_id=document.id,
            status="candidate",
            verification=verification,
        )
        session.add(edge)
        created.append(edge)

    session.commit()
    for edge in created:
        session.refresh(edge)
    return created
