import pytest
from app import models  # noqa: F401
from app.db import get_session
from app.main import app
from app.models import Entity
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


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


def _seed_entities(db_engine, *names):
    s = Session(db_engine)
    s.add_all([Entity(name=n, aliases=[]) for n in names])
    s.commit()
    s.close()


def test_create_document_and_extract_with_fallback(client, db_engine):
    # Seed the two entities so the fallback proposer (which only matches known
    # entity names) can emit a candidate for the passage that mentions both.
    _seed_entities(db_engine, "OpenAI", "CoreWeave")

    doc_resp = client.post(
        "/documents",
        json={"title": "CoreWeave S-1", "raw_text": "OpenAI committed $11.9 billion to CoreWeave through 2030."},
    )
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["id"]

    extract_resp = client.post(f"/documents/{doc_id}/extract", params={"provider": "fallback"})
    assert extract_resp.status_code == 200
    body = extract_resp.json()
    assert body["provider"] == "fallback"
    assert body["document_id"] == doc_id
    assert body["candidates_created"] == 1

    # verify the candidate landed in the DB (queried directly — the /edges review
    # endpoints are added in Task 5; this task's edges router is still a placeholder)
    from app.models import Edge

    s = Session(db_engine)
    try:
        edges = s.query(Edge).all()
        assert len(edges) == 1
        assert edges[0].status == "candidate"
        assert edges[0].value == 11.9
    finally:
        s.close()


def test_extract_unknown_document_404(client):
    resp = client.post("/documents/nope/extract", params={"provider": "fallback"})
    assert resp.status_code == 404


def test_extract_uses_document_level_orchestrator(client, db_engine, monkeypatch):
    from app.extraction.schema import ExtractionResult
    from app.routers import documents as documents_router

    _seed_entities(db_engine, "Amazon", "Anthropic")
    raw_text = "A" * 130_000 + "Amazon invested $8 billion in Anthropic."
    create_resp = client.post("/documents", json={"title": "Amazon 10-K", "raw_text": raw_text})
    doc_id = create_resp.json()["id"]
    seen = {}

    def fake_extract(text, known_entities, document_id="doc", **kwargs):
        seen.update(
            text=text,
            known_entities=known_entities,
            document_id=document_id,
            kwargs=kwargs,
        )
        return ExtractionResult(candidates=[])

    monkeypatch.setattr(documents_router, "extract_document_candidates", fake_extract)
    resp = client.post(f"/documents/{doc_id}/extract", params={"provider": "fallback"})

    assert resp.status_code == 200
    assert seen["text"] == raw_text
    assert set(seen["known_entities"]) == {"Amazon", "Anthropic"}
    assert seen["document_id"] == doc_id
    assert seen["kwargs"]["provider"] == "fallback"


def test_list_entities_empty(client):
    resp = client.get("/entities")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_document_from_url_reads_via_reader(client, db_engine, monkeypatch):
    from app.routers import documents as documents_router

    monkeypatch.setattr(
        documents_router,
        "fetch_url_text",
        lambda url: "OpenAI has committed to pay us up to approximately $11.9 billion through October 2030.",
    )
    resp = client.post(
        "/documents/from_url",
        json={"url": "https://www.sec.gov/Archives/edgar/data/1769628/x.htm", "title": "CoreWeave S-1/A"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "CoreWeave S-1/A"

    from app.models import Document

    s = Session(db_engine)
    try:
        doc = s.query(Document).one()
        assert "11.9 billion" in doc.raw_text
        assert doc.url == "https://www.sec.gov/Archives/edgar/data/1769628/x.htm"
    finally:
        s.close()


def test_create_document_from_url_502_on_reader_failure(client, monkeypatch):
    from app.routers import documents as documents_router

    def _boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(documents_router, "fetch_url_text", _boom)
    resp = client.post("/documents/from_url", json={"url": "https://x"})
    assert resp.status_code == 502
