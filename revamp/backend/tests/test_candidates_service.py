from app.extraction.schema import CandidateEdge, ExtractionResult
from app.models import Document, Edge, Entity
from app.services.candidates import persist_candidates


def _result() -> ExtractionResult:
    c = CandidateEdge(
        source_entity="OpenAI",
        target_entity="CoreWeave",
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        exact_passage="OpenAI committed $11.9 billion to CoreWeave through 2030.",
        document_id="doc-1",
        permitted_operation="report ceiling as exposure",
        unsupported_operation="treat as realized loss",
        missing_information=["PD"],
        evidence_class="reported",
        confidence_note="verbatim",
    )
    return ExtractionResult(candidates=[c])


def test_persist_creates_candidate_edge_with_verification(db_session):
    doc = Document(title="CoreWeave S-1", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    db_session.add(doc)
    db_session.flush()

    edges = persist_candidates(db_session, _result(), doc)

    assert len(edges) == 1
    e = db_session.get(Edge, edges[0].id)
    assert e.status == "candidate"
    assert e.relationship_type == "purchase_obligation"
    assert e.value == 11.9
    assert e.document_id == doc.id
    assert e.passage_id is not None
    assert e.verification["overall"] == "pass"
    # entities were created and linked
    assert e.source_entity_id is not None
    assert e.target_entity_id is not None


def test_entities_are_deduplicated(db_session):
    doc = Document(title="d", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    db_session.add(doc)
    db_session.flush()

    persist_candidates(db_session, _result(), doc)
    persist_candidates(db_session, _result(), doc)

    assert db_session.query(Entity).filter_by(name="OpenAI").count() == 1
    assert db_session.query(Edge).count() == 2
