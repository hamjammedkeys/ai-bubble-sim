from pathlib import Path

from fragility_map.extraction.relationships import (
    estimate_confidence,
    extract_relationship_candidates,
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
