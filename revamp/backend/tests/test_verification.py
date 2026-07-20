from app.extraction.schema import CandidateEdge
from app.verification import verify_candidate


def _candidate(**over) -> CandidateEdge:
    base = dict(
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
        missing_information=["PD", "LGD"],
        evidence_class="reported",
        confidence_note="verbatim",
    )
    base.update(over)
    return CandidateEdge(**base)


DOC = "In 2024, OpenAI committed $11.9 billion to CoreWeave through 2030 for compute."


def test_valid_candidate_passes():
    v = verify_candidate(_candidate(), DOC, document_exists=True)
    assert v["passage_found"] is True
    assert v["match_score"] >= 92
    assert v["number_found"] is True
    assert v["entities_found"] is True
    assert v["unit_allowed"] is True
    assert v["source_valid"] is True
    assert v["overall"] == "pass"


def test_fabricated_number_flags():
    # value not present in the passage
    v = verify_candidate(_candidate(value=99.9), DOC, document_exists=True)
    assert v["number_found"] is False
    assert v["overall"] == "flag"


def test_passage_not_in_document_flags():
    v = verify_candidate(_candidate(exact_passage="OpenAI acquired CoreWeave outright."), DOC, document_exists=True)
    assert v["passage_found"] is False
    assert v["overall"] == "flag"


def test_missing_document_flags():
    v = verify_candidate(_candidate(), DOC, document_exists=False)
    assert v["source_valid"] is False
    assert v["overall"] == "flag"


def test_null_value_skips_number_check():
    v = verify_candidate(_candidate(value=None, unit=None, evidence_class="unknown"), DOC, document_exists=True)
    assert v["number_found"] is None
    assert v["overall"] == "pass"


def test_bad_unit_flags():
    v = verify_candidate(_candidate(unit="bananas"), DOC, document_exists=True)
    assert v["unit_allowed"] is False
    assert v["overall"] == "flag"


def test_small_value_does_not_false_match_inside_larger_number():
    # value=1 must NOT be considered "found" just because "1" appears inside "$11.9 billion"
    v = verify_candidate(
        _candidate(value=1.0, unit="percent", metric="ownership_pct"),
        DOC,
        document_exists=True,
    )
    assert v["number_found"] is False
    assert v["overall"] == "flag"


def test_standalone_integer_value_matches():
    doc = "Microsoft holds a 27% ownership interest in OpenAI."
    v = verify_candidate(
        _candidate(
            value=27.0,
            unit="percent",
            metric="ownership_pct",
            exact_passage="Microsoft holds a 27% ownership interest in OpenAI.",
            source_entity="Microsoft",
            target_entity="OpenAI",
        ),
        doc,
        document_exists=True,
    )
    assert v["number_found"] is True
    assert v["overall"] == "pass"
