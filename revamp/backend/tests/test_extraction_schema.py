import pytest
from pydantic import ValidationError

from app.extraction.schema import CandidateEdge, ExtractionResult


def _valid_candidate() -> dict:
    return {
        "source_entity": "OpenAI",
        "target_entity": "CoreWeave",
        "relationship_type": "purchase_obligation",
        "metric": "contract_value",
        "value": 11.9,
        "unit": "usd_billions",
        "period": "through_2030",
        "exact_passage": "OpenAI committed $11.9 billion to CoreWeave.",
        "document_id": "doc-1",
        "permitted_operation": "report disclosed ceiling as exposure",
        "unsupported_operation": "treat as realized loss",
        "missing_information": ["PD", "LGD"],
        "evidence_class": "reported",
        "confidence_note": "verbatim from S-1",
    }


def test_candidate_edge_accepts_valid():
    c = CandidateEdge(**_valid_candidate())
    assert c.value == 11.9
    assert c.missing_information == ["PD", "LGD"]


def test_value_optional_and_missing_info_defaults():
    data = _valid_candidate()
    data["value"] = None
    data["missing_information"] = []
    c = CandidateEdge(**data)
    assert c.value is None


def test_rejects_bad_relationship_type():
    data = _valid_candidate()
    data["relationship_type"] = "made_up_type"
    with pytest.raises(ValidationError):
        CandidateEdge(**data)


def test_rejects_bad_evidence_class():
    data = _valid_candidate()
    data["evidence_class"] = "guessed"
    with pytest.raises(ValidationError):
        CandidateEdge(**data)


def test_extraction_result_wraps_candidates():
    r = ExtractionResult(candidates=[CandidateEdge(**_valid_candidate())])
    assert len(r.candidates) == 1
