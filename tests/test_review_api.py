from pathlib import Path

from fastapi.testclient import TestClient

from fragility_map.api import review
from fragility_map.api.server import app

client = TestClient(app)


def _propose() -> dict:
    review.reset_session()
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    response = client.post(
        "/api/extraction/propose",
        json={
            "source_id": "coreweave-s1a",
            "source_accession": "0001640147-25-000001",
            "source_company_id": "openai",
            "target_company_id": "coreweave",
            "filing_text": text,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_propose_returns_verified_blue_striped_candidates() -> None:
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    body = _propose()
    views = {c["candidate"]["relationship_type"]: c for c in body["candidates"]}

    top = views["take_or_pay"]
    assert top["candidate"]["status"] == "proposed"
    assert top["verification"]["mechanically_valid"] is True
    assert top["verification"]["semantic_interpretation"] == "pending_human_review"
    assert {c["name"] for c in top["verification"]["checks"]} == {
        "quoted_text",
        "numeric_token",
        "entities",
        "period",
        "unit",
        "arithmetic",
        "accession",
        "supersession",
    }
    quote = top["candidate"]["quoted_text"]
    start, end = top["highlight"]["start"], top["highlight"]["end"]
    assert end - start == len(quote)
    assert text[start:end] == quote
