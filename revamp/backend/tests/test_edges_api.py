import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models import Document, Edge, Entity
from app import models  # noqa: F401


@pytest.fixture
def client(db_engine):
    def _override():
        session = Session(db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_candidate(db_engine) -> str:
    s = Session(db_engine)
    src = Entity(name="OpenAI", aliases=[])
    tgt = Entity(name="CoreWeave", aliases=[])
    doc = Document(title="d", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    s.add_all([src, tgt, doc])
    s.flush()
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
        status="candidate",
        verification={"overall": "pass"},
    )
    s.add(edge)
    s.commit()
    edge_id = edge.id
    s.close()
    return edge_id


def test_edge_detail_includes_citation(client, db_engine):
    from app.models import Document, Edge, Entity, Passage

    s = Session(db_engine)
    src = Entity(name="OpenAI", aliases=[])
    tgt = Entity(name="CoreWeave", aliases=[])
    doc = Document(
        title="CoreWeave S-1",
        url="https://www.sec.gov/example",
        raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.",
    )
    s.add_all([src, tgt, doc])
    s.flush()
    passage = Passage(document_id=doc.id, text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    s.add(passage)
    s.flush()
    edge = Edge(
        source_entity_id=src.id,
        target_entity_id=tgt.id,
        relationship_type="purchase_obligation",
        evidence_class="reported",
        passage_id=passage.id,
        document_id=doc.id,
        status="approved",
    )
    s.add(edge)
    s.commit()
    edge_id = edge.id
    s.close()

    body = client.get(f"/edges/{edge_id}").json()
    assert body["passage_text"] == "OpenAI committed $11.9 billion to CoreWeave through 2030."
    assert body["document_title"] == "CoreWeave S-1"
    assert body["document_url"] == "https://www.sec.gov/example"


def test_candidates_list_and_approve(client, db_engine):
    edge_id = _seed_candidate(db_engine)

    cand = client.get("/edges/candidates")
    assert cand.status_code == 200
    assert len(cand.json()) == 1
    assert cand.json()[0]["id"] == edge_id

    approve = client.post(f"/edges/{edge_id}/approve", json={"reviewed_by": "dawn"})
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    # now it is no longer a candidate
    assert client.get("/edges/candidates").json() == []
    # and re-approving is a conflict
    assert client.post(f"/edges/{edge_id}/approve", json={}).status_code == 409


def test_get_edge_and_filter_by_status(client, db_engine):
    edge_id = _seed_candidate(db_engine)
    assert client.get(f"/edges/{edge_id}").json()["id"] == edge_id
    assert client.get("/edges", params={"status": "approved"}).json() == []
    assert len(client.get("/edges", params={"status": "candidate"}).json()) == 1


def test_reject_and_missing(client, db_engine):
    edge_id = _seed_candidate(db_engine)
    assert client.post(f"/edges/{edge_id}/reject", json={}).json()["status"] == "rejected"
    assert client.get("/edges/does-not-exist").status_code == 404
    assert client.post("/edges/does-not-exist/approve", json={}).status_code == 404


def test_edit_reruns_verification(client, db_engine):
    edge_id = _seed_candidate(db_engine)
    resp = client.post(f"/edges/{edge_id}/edit", json={"value": 99.9})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "candidate"
    assert body["value"] == 99.9
    assert body["verification"]["overall"] == "flag"
