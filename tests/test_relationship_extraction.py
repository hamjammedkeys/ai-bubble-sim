from pathlib import Path

from fragility_map.extraction.candidates import (
    CandidateStatus,
    RelationshipCandidateV2,
    propose_candidates,
)
from fragility_map.extraction.lifecycle import CandidateLifecycle, promote_approved
from fragility_map.extraction.proposers import KeywordProposer
from fragility_map.extraction.relationships import (
    estimate_confidence,
    extract_relationship_candidates,
)
from fragility_map.extraction.verifier import (
    SourceManifestEntry,
    VerificationResult,
    verify_candidate,
)


def test_extracts_customer_concentration_candidate() -> None:
    text = Path("tests/fixtures/sec_customer_concentration.txt").read_text(encoding="utf-8")
    candidates = extract_relationship_candidates("nvda", "nvda-sec_10k-2025-02-26", text)

    assert len(candidates) == 1
    assert candidates[0].evidence_type == "customer_concentration"
    assert candidates[0].percentage == 0.19
    assert candidates[0].confidence == 0.9


def test_extracts_purchase_commitment_candidate() -> None:
    text = Path("tests/fixtures/pdf_supplier_commitment.txt").read_text(encoding="utf-8")
    candidates = extract_relationship_candidates("msft", "msft-investor_pdf-2025-07-30", text)

    assert len(candidates) == 1
    assert candidates[0].evidence_type == "purchase_commitment"
    assert candidates[0].amount == 4_000_000_000
    assert candidates[0].confidence == 1.0


def test_confidence_rules_do_not_mix_with_economic_impact() -> None:
    assert estimate_confidence("exact_amount", True) == 1.0
    assert estimate_confidence("customer_concentration", True) == 0.9
    assert estimate_confidence("relationship_disclosure", False) == 0.3


class StubProposer:
    def propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]:
        return [
            RelationshipCandidateV2(
                candidate_id="cand-1",
                source_id=source_id,
                source_accession="0000123456-25-000001",
                source_company_id="msft",
                target_company_id="coreweave",
                relationship_type="take_or_pay",
                quoted_text=(
                    "Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave."
                ),
                numeric_token="$4 billion",
                value=4_000_000_000,
                unit="USD",
                period="through 2030",
                supported_rule="reported purchase commitment envelope",
                unsupported_inference="the commitment is specifically with CoreWeave",
            )
        ]


def test_candidate_is_typed_and_starts_proposed() -> None:
    candidate = StubProposer().propose("msft-filing", "filing text")[0]
    assert candidate.status is CandidateStatus.PROPOSED
    assert candidate.value == 4_000_000_000


def test_proposal_boundary_is_stubbable() -> None:
    assert [c.candidate_id for c in propose_candidates(StubProposer(), "x", "y")] == ["cand-1"]


def test_verifier_reports_each_check_and_keeps_semantics_pending() -> None:
    text = Path("tests/fixtures/filing_with_candidate.txt").read_text(encoding="utf-8")
    result = verify_candidate(
        text,
        StubProposer().propose("msft-filing", text)[0],
        [SourceManifestEntry("0000123456-25-000001", "msft-filing")],
    )
    assert result.mechanically_valid is True
    assert result.semantic_interpretation == "pending_human_review"
    assert {c.name for c in result.checks} == {
        "quoted_text",
        "numeric_token",
        "entities",
        "period",
        "unit",
        "arithmetic",
        "accession",
        "supersession",
    }


def test_verifier_blocks_missing_quote_and_superseded_accession() -> None:
    text = "Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave."
    candidate = (
        StubProposer().propose("msft-filing", text)[0].model_copy(update={"quoted_text": "missing"})
    )
    result = verify_candidate(
        text,
        candidate,
        [SourceManifestEntry("0000123456-25-000001", "msft-filing")],
        {"0000123456-25-000001"},
    )
    assert {c.name for c in result.checks if not c.passed} == {"quoted_text", "supersession"}


def test_approval_requires_verification_and_writes_audit() -> None:
    text = Path("tests/fixtures/filing_with_candidate.txt").read_text(encoding="utf-8")
    candidate = StubProposer().propose("msft-filing", text)[0]
    verification = verify_candidate(
        text, candidate, [SourceManifestEntry("0000123456-25-000001", "msft-filing")]
    )
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, verification)
    approved = lifecycle.approve("cand-1", "reviewer-1", "quote and amount confirmed")
    assert approved.status is CandidateStatus.APPROVED
    assert lifecycle.audit_log()[-1].to_status is CandidateStatus.APPROVED
    assert promote_approved(approved, verification).structure_type.value == "take_or_pay"


def test_rejection_is_terminal_for_promotion_and_logged() -> None:
    candidate = StubProposer().propose("msft-filing", "filing text")[0]
    invalid = VerificationResult("cand-1", (), "pending_human_review", False)
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, invalid)
    rejected = lifecycle.reject(
        "cand-1", "judge", "general portfolio language does not identify CoreWeave"
    )
    assert rejected.status is CandidateStatus.REJECTED
    assert lifecycle.audit_log()[-1].reason.startswith("general portfolio")


def test_signature_integrity_rejects_generic_portfolio_language() -> None:
    text = Path("tests/fixtures/filing_with_candidate.txt").read_text(encoding="utf-8")
    candidate = (
        StubProposer()
        .propose("msft-filing", text)[0]
        .model_copy(update={"unsupported_inference": "CoreWeave is the named counterparty"})
    )
    verification = verify_candidate(
        text,
        candidate,
        [SourceManifestEntry("0000123456-25-000001", "msft-filing")],
    )
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, verification)
    rejected = lifecycle.reject(
        "cand-1", "judge", "general portfolio language does not identify CoreWeave"
    )
    assert rejected.status is CandidateStatus.REJECTED
    assert lifecycle.audit_log()[-1].reason == (
        "general portfolio language does not identify CoreWeave"
    )


def test_keyword_proposer_extracts_take_or_pay_and_concentration() -> None:
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    proposer = KeywordProposer(
        source_accession="0001640147-25-000001",
        source_company_id="openai",
        target_company_id="coreweave",
    )
    candidates = proposer.propose("coreweave-s1a", text)
    by_type = {c.relationship_type: c for c in candidates}

    top = by_type["take_or_pay"]
    assert top.value == 11_900_000_000
    assert top.unit == "USD"
    assert top.quoted_text in text
    assert top.status is CandidateStatus.PROPOSED

    conc = by_type["customer_concentration"]
    assert conc.value == 62.0
    assert conc.quoted_text == "Microsoft accounted for 62% of our revenue in 2024."
