from pathlib import Path

from fragility_map.db.repository import FragilityRepository
from fragility_map.extraction.candidates import CandidateStatus, RelationshipCandidateV2
from fragility_map.extraction.lifecycle import AuditEvent
from fragility_map.extraction.verifier import VerificationCheck, VerificationResult
from fragility_map.ingestion.companies import CompanyConfig


def test_repository_creates_schema_and_upserts_companies(tmp_path: Path) -> None:
    repo = FragilityRepository(tmp_path / "test.duckdb")
    repo.create_schema()

    repo.upsert_companies(
        [
            CompanyConfig(
                company_id="msft",
                ticker="MSFT",
                name="Microsoft",
                sector_group="cloud_platform",
                country="US",
            )
        ]
    )

    companies = repo.list_companies()

    assert companies == [
        {
            "company_id": "msft",
            "ticker": "MSFT",
            "name": "Microsoft",
            "sector_group": "cloud_platform",
            "country": "US",
        }
    ]


def test_repository_round_trips_candidate_verification_and_audit(tmp_path: Path) -> None:
    repo = FragilityRepository(tmp_path / "review.duckdb")
    repo.create_schema()
    candidate = RelationshipCandidateV2(
        candidate_id="cand-1",
        source_id="msft-filing",
        source_accession="acc-1",
        source_company_id="msft",
        target_company_id="coreweave",
        relationship_type="take_or_pay",
        quoted_text="Microsoft purchase commitments",
        numeric_token="$4 billion",
        value=4_000_000_000,
        unit="USD",
        period="2030",
        supported_rule="envelope",
        unsupported_inference="counterparty",
    )
    verification = VerificationResult(
        "cand-1", (VerificationCheck("quoted_text", True, "found"),), "pending_human_review", True
    )
    repo.save_candidate(candidate, verification)
    repo.record_candidate_audit(
        AuditEvent(
            "cand-1",
            CandidateStatus.PROPOSED,
            CandidateStatus.APPROVED,
            "reviewer-1",
            "confirmed",
            True,
        )
    )
    stored = repo.get_candidate("cand-1")
    assert stored is not None
    assert stored["verification"]["mechanically_valid"] is True
    assert repo.list_candidate_audit("cand-1")[0]["to_status"] == "approved"
