from pathlib import Path

from fastapi.testclient import TestClient

from fragility_map.api import review
from fragility_map.api.server import app

client = TestClient(app)


def _propose_and(approve: bool) -> None:
    review.reset_session()
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    client.post(
        "/api/extraction/propose",
        json={
            "source_id": "coreweave-s1a",
            "source_accession": "0001640147-25-000001",
            "source_company_id": "openai",
            "target_company_id": "coreweave",
            "filing_text": text,
        },
    )
    if approve:
        client.post(
            "/api/extraction/approve",
            json={
                "candidate_id": "coreweave-s1a-take_or_pay",
                "reviewer_id": "judge",
                "reason": "confirmed",
            },
        )


def test_seeded_equity_impact_is_always_present() -> None:
    review.reset_session()
    result = client.post("/api/scenario/credit-event", json={}).json()
    assert result["nodes"]["msft"]["quantified_impact"] == -2_700_000_000
    msft_edge = next(e for e in result["edges"] if e["target"] == "msft")
    assert msft_edge["tier"] == "solid_red"
    assert msft_edge["result_kind"] == "impact"


def test_approved_take_or_pay_activates_orange_exposure() -> None:
    _propose_and(approve=True)
    result = client.post("/api/scenario/credit-event", json={}).json()
    assert result["nodes"]["coreweave"]["activated_exposure"] == 11_900_000_000
    cw_edge = next(e for e in result["edges"] if e["target"] == "coreweave")
    assert cw_edge["tier"] == "solid_orange"
    assert cw_edge["result_kind"] == "exposure"


def test_without_approval_no_coreweave_exposure() -> None:
    _propose_and(approve=False)
    result = client.post("/api/scenario/credit-event", json={}).json()
    assert "coreweave" not in result["nodes"] or (
        result["nodes"]["coreweave"]["activated_exposure"] is None
    )
