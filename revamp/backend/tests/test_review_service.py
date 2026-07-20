import pytest

from app.models import Document, Edge, Entity, Passage
from app.services.review import InvalidTransition, approve_edge, edit_edge, reject_edge


def _candidate_edge(session) -> Edge:
    src = Entity(name="OpenAI", aliases=[])
    tgt = Entity(name="CoreWeave", aliases=[])
    doc = Document(title="d", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    session.add_all([src, tgt, doc])
    session.flush()
    passage = Passage(
        document_id=doc.id,
        text="OpenAI committed $11.9 billion to CoreWeave through 2030.",
    )
    session.add(passage)
    session.flush()
    edge = Edge(
        source_entity_id=src.id,
        target_entity_id=tgt.id,
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        evidence_class="reported",
        document_id=doc.id,
        passage_id=passage.id,
        status="candidate",
        verification={"overall": "pass"},
    )
    session.add(edge)
    session.commit()
    return edge


def test_approve_sets_status_and_reviewer(db_session):
    edge = _candidate_edge(db_session)
    result = approve_edge(db_session, edge.id, reviewed_by="dawn")
    assert result.status == "approved"
    assert result.reviewed_by == "dawn"
    assert result.reviewed_at is not None


def test_reject_sets_status(db_session):
    edge = _candidate_edge(db_session)
    result = reject_edge(db_session, edge.id)
    assert result.status == "rejected"
    assert result.reviewed_at is not None


def test_cannot_approve_already_approved(db_session):
    edge = _candidate_edge(db_session)
    approve_edge(db_session, edge.id)
    with pytest.raises(InvalidTransition):
        approve_edge(db_session, edge.id)


def test_edit_updates_fields_reruns_verifier_and_stays_candidate(db_session):
    edge = _candidate_edge(db_session)

    # Edit to a value NOT present in the passage -> verifier flags it.
    flagged = edit_edge(db_session, edge.id, {"value": 99.9})
    assert flagged.status == "candidate"
    assert flagged.value == 99.9
    assert flagged.verification["number_found"] is False
    assert flagged.verification["overall"] == "flag"

    # Edit back to the value that IS in the passage ($11.9 billion) -> passes.
    passing = edit_edge(db_session, edge.id, {"value": 11.9})
    assert passing.verification["number_found"] is True
    assert passing.verification["overall"] == "pass"


def test_edit_rejected_edge_raises(db_session):
    edge = _candidate_edge(db_session)
    reject_edge(db_session, edge.id)
    with pytest.raises(InvalidTransition):
        edit_edge(db_session, edge.id, {"value": 5.0})


def test_missing_edge_raises_keyerror(db_session):
    with pytest.raises(KeyError):
        approve_edge(db_session, "does-not-exist")
