from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fragility_map.api.server import app
from fragility_map.db.repository import FragilityRepository
from fragility_map.extraction.candidates import RelationshipCandidateV2
from fragility_map.extraction.lifecycle import CandidateLifecycle
from fragility_map.extraction.verifier import SourceManifestEntry, verify_candidate
from fragility_map.ingestion.official_pdfs import SourceRecord
from fragility_map.seed.hero import hero_relationships
from fragility_map.settings import get_paths


def test_compound_credit_event_returns_impact_exposure_and_dissolve() -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        json={
            "incremental_gaap_loss": 10_000_000_000,
            "credit_status": "severe_distress",
            "default_status": "not_defaulted",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["scenario"]["language"]
        == "calculated Impact plus activated Exposure; downstream loss not identifiable"
    )
    assert (
        next(edge for edge in payload["edges"] if edge["relationshipId"] == "openai-msft")[
            "tier"
        ]
        == "solid_red"
    )
    assert (
        next(
            edge
            for edge in payload["edges"]
            if edge["relationshipId"] == "openai-coreweave"
        )["resultKind"]
        == "exposure"
    )
    assert (
        next(
            edge for edge in payload["edges"] if edge["relationshipId"] == "coreweave-nvda"
        )["value"]
        is None
    )


def test_compound_credit_event_returns_realized_loss_guardrail() -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        json={
            "incremental_gaap_loss": 10_000_000_000,
            "credit_status": "severe_distress",
            "default_status": "not_defaulted",
        },
    )

    assert response.status_code == 200
    guardrail = next(
        edge
        for edge in response.json()["edges"]
        if edge["relationshipId"] == "openai-coreweave-realized-loss"
    )
    assert guardrail["tier"] == "dashed_amber"
    assert guardrail["resultKind"] == "realized_loss_unidentifiable"
    assert guardrail["value"] is None


def test_compound_credit_event_serializes_primary_evidence_for_every_numeric_hero_edge() -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        json={
            "incremental_gaap_loss": 10_000_000_000,
            "credit_status": "severe_distress",
            "default_status": "not_defaulted",
        },
    )

    assert response.status_code == 200
    edges = {edge["relationshipId"]: edge for edge in response.json()["edges"]}
    numeric_relationships = [
        relationship
        for relationship in hero_relationships()
        if relationship.ownership_share is not None
        or relationship.concentration is not None
        or relationship.committed_envelope is not None
    ]
    for relationship in numeric_relationships:
        edge = edges[relationship.relationship_id]
        assert edge["sourceAccession"] == relationship.source_accession
        assert edge["evidenceQuote"] == relationship.evidence_quote
        assert edge["sourceLocation"] == relationship.source_location


def test_normal_not_defaulted_event_does_not_emit_unactivated_downstream_dissolve() -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        json={
            "incremental_gaap_loss": 10_000_000_000,
            "credit_status": "normal",
            "default_status": "not_defaulted",
        },
    )

    assert response.status_code == 200
    assert all(
        edge["relationshipId"] != "coreweave-nvda" for edge in response.json()["edges"]
    )


def test_compound_credit_event_rejects_missing_or_invalid_state() -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event", json={"incremental_gaap_loss": -1}
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["tier", "numeric_result"])
def test_compound_credit_event_rejects_client_result_fields(field: str) -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        json={
            "incremental_gaap_loss": 10_000_000_000,
            "credit_status": "severe_distress",
            "default_status": "not_defaulted",
            field: "client-provided",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize("loss", ["NaN", "Infinity"])
def test_compound_credit_event_rejects_nonfinite_loss(loss: str) -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        content=(
            f'{{"incremental_gaap_loss": {loss}, "credit_status": "severe_distress", '
            '"default_status": "not_defaulted"}'
        ),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def _candidate() -> RelationshipCandidateV2:
    return RelationshipCandidateV2(
        candidate_id="cand-1",
        source_id="msft-filing",
        source_accession="acc-1",
        source_company_id="msft",
        target_company_id="coreweave",
        relationship_type="take_or_pay",
        quoted_text="Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave.",
        numeric_token="$4 billion",
        value=4_000_000_000,
        unit="USD",
        period="through 2030",
        supported_rule="reported purchase commitment envelope",
        unsupported_inference="the commitment is specifically with CoreWeave",
    )


def _configure_review_store(tmp_path: Path, monkeypatch) -> FragilityRepository:
    filing_text = _candidate().quoted_text
    filing_path = tmp_path / "msft-filing.txt"
    filing_path.write_text(filing_text, encoding="utf-8")
    repo = FragilityRepository(tmp_path / "review.duckdb")
    repo.create_schema()
    repo.upsert_sources(
        [
            SourceRecord(
                source_id="msft-filing",
                company_id="msft",
                source_type="10-k",
                source_date=date(2025, 1, 1),
                url="https://example.com/msft-filing",
                local_path=str(filing_path),
                extraction_status="complete",
            )
        ]
    )
    candidate = _candidate()
    verification = verify_candidate(
        filing_text,
        candidate,
        [SourceManifestEntry(candidate.source_accession, candidate.source_id)],
    )
    repo.save_candidate(candidate, verification)
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, verification)
    monkeypatch.setattr(app.state, "review_repository", repo, raising=False)
    monkeypatch.setattr(app.state, "review_lifecycle", lifecycle, raising=False)
    return repo


def test_review_routes_persist_transition_and_reverify_edit(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _configure_review_store(tmp_path, monkeypatch)
    client = TestClient(app)

    listed = client.get("/api/v2/review/candidates")

    assert listed.status_code == 200
    assert listed.json()["reviewCandidates"][0]["candidateId"] == "cand-1"
    assert listed.json()["reviewCandidates"][0]["verificationChecks"][0]["name"] == "quoted_text"

    approved = client.post(
        "/api/v2/review/cand-1/approve",
        json={"reviewer_id": "reviewer-1", "reason": "quote and amount confirmed"},
    )

    assert approved.status_code == 200
    assert repo.get_candidate("cand-1")["status"] == "approved"
    assert approved.json()["auditLog"][-1]["toStatus"] == "approved"

    invalid_transition = client.post(
        "/api/v2/review/cand-1/approve",
        json={"reviewer_id": "reviewer-1", "reason": "again"},
    )

    assert invalid_transition.status_code == 409

    edited_candidate = _candidate().model_copy(update={"value": 5_000_000_000})
    edited = client.post(
        "/api/v2/review/cand-1/edit",
        json={
            "candidate": edited_candidate.model_dump(mode="json"),
            "reviewer_id": "reviewer-2",
            "reason": "corrected amount",
        },
    )

    assert edited.status_code == 200
    assert repo.get_candidate("cand-1")["mechanically_valid"] is False
    assert edited.json()["auditLog"][-1]["verificationValid"] is False

    assert client.post(
        "/api/v2/review/missing/reject",
        json={"reviewer_id": "reviewer-1", "reason": "not found"},
    ).status_code == 404

    assert client.post(
        "/api/v2/review/cand-1/edit",
        json={"reviewer_id": "reviewer-2", "reason": "missing candidate"},
    ).status_code == 422

    invalid_candidate = _candidate().model_dump(mode="json")
    invalid_candidate["numeric_result"] = -2_700_000_000
    assert client.post(
        "/api/v2/review/cand-1/edit",
        json={
            "candidate": invalid_candidate,
            "reviewer_id": "reviewer-2",
            "reason": "client result fields are forbidden",
        },
    ).status_code == 422

    mismatched_candidate = _candidate().model_copy(update={"candidate_id": "cand-other"})
    assert client.post(
        "/api/v2/review/cand-1/edit",
        json={
            "candidate": mismatched_candidate.model_dump(mode="json"),
            "reviewer_id": "reviewer-2",
            "reason": "candidate ID must match the route",
        },
    ).status_code == 422

    assert client.post(
        "/api/v2/review/cand-1/approve",
        json={"reviewer_id": "  ", "reason": "valid reason"},
    ).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "forged-source"),
        ("source_accession", "forged-accession"),
        ("source_company_id", "forged-company"),
    ],
)
def test_review_edit_rejects_forged_source_identity(
    tmp_path: Path, monkeypatch, field: str, value: str
) -> None:
    repo = _configure_review_store(tmp_path, monkeypatch)
    forged_candidate = _candidate().model_copy(update={field: value})

    response = TestClient(app).post(
        "/api/v2/review/cand-1/edit",
        json={
            "candidate": forged_candidate.model_dump(mode="json"),
            "reviewer_id": "reviewer-1",
            "reason": "attempted source forgery",
        },
    )

    assert response.status_code == 422
    stored = repo.get_candidate("cand-1")
    assert stored is not None
    assert stored["candidate"][field] == _candidate().model_dump(mode="json")[field]


def test_fresh_review_store_seeds_a_pending_candidate_without_promoting_it(
    tmp_path: Path, monkeypatch
) -> None:
    import fragility_map.api.server as api_server

    monkeypatch.setattr(api_server, "get_paths", lambda: get_paths(tmp_path))
    monkeypatch.setattr(app.state, "review_repository", None, raising=False)
    monkeypatch.setattr(app.state, "review_lifecycle", None, raising=False)

    response = TestClient(app).get("/api/v2/review/candidates")

    assert response.status_code == 200
    candidate = response.json()["reviewCandidates"][0]
    assert candidate["status"] == "proposed"
    assert candidate["quotedText"]
    assert candidate["sourceAccession"]
    assert candidate["mechanicallyValid"] is True
    repository = app.state.review_repository
    assert repository.get_candidate(candidate["candidateId"])["status"] == "proposed"
