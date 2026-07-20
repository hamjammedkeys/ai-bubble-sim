import types

import pytest
from app.extraction import adapter
from app.extraction.adapter import build_messages, extract_candidates
from app.extraction.schema import ExtractionResult


def _fake_openai_client(parsed: ExtractionResult):
    """A stand-in for the OpenAI SDK's .beta.chat.completions.parse surface."""
    message = types.SimpleNamespace(parsed=parsed)
    choice = types.SimpleNamespace(message=message)
    response = types.SimpleNamespace(choices=[choice])

    class _Parser:
        def parse(self, **kwargs):
            self.last_kwargs = kwargs
            return response

    parser = _Parser()
    beta = types.SimpleNamespace(chat=types.SimpleNamespace(completions=parser))
    return types.SimpleNamespace(beta=beta), parser


def test_fallback_provider_routes_to_proposer():
    text = "OpenAI committed $11.9 billion to CoreWeave."
    result = extract_candidates(text, ["OpenAI", "CoreWeave"], provider="fallback")
    assert len(result.candidates) == 1
    assert result.candidates[0].value == 11.9


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        extract_candidates("x", [], provider="does_not_exist")


def test_openai_branch_maps_response_from_injected_client():
    parsed = ExtractionResult.model_validate(
        {
            "candidates": [
                {
                    "source_entity": "OpenAI",
                    "target_entity": "CoreWeave",
                    "relationship_type": "purchase_obligation",
                    "metric": "contract_value",
                    "value": 11.9,
                    "unit": "usd_billions",
                    "period": "through_2030",
                    "exact_passage": "OpenAI committed $11.9 billion to CoreWeave.",
                    "document_id": "llm-hallucinated-doc",
                    "permitted_operation": "x",
                    "unsupported_operation": "y",
                    "missing_information": ["PD"],
                    "evidence_class": "reported",
                    "confidence_note": "z",
                }
            ]
        }
    )
    client, parser = _fake_openai_client(parsed)
    result = extract_candidates(
        "OpenAI committed $11.9 billion to CoreWeave.",
        ["OpenAI", "CoreWeave"],
        document_id="s1",
        provider="openai",
        client=client,
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].relationship_type == "purchase_obligation"
    # Caller's document_id must override the LLM's hallucinated value.
    assert result.candidates[0].document_id == "s1"
    # The request used temperature 0 and the Pydantic model as response_format.
    assert parser.last_kwargs["temperature"] == 0
    assert parser.last_kwargs["response_format"] is ExtractionResult


def test_openai_units_are_normalized_to_canonical_vocabulary():
    parsed = ExtractionResult.model_validate(
        {
            "candidates": [
                {
                    "source_entity": "OpenAI",
                    "target_entity": "CoreWeave",
                    "relationship_type": "purchase_obligation",
                    "metric": "contract_value",
                    "value": 11.9,
                    "unit": "billion USD",
                    "period": "through_2030",
                    "exact_passage": "OpenAI committed $11.9 billion to CoreWeave.",
                    "document_id": "x",
                    "permitted_operation": "a",
                    "unsupported_operation": "b",
                    "missing_information": [],
                    "evidence_class": "reported",
                    "confidence_note": "c",
                }
            ]
        }
    )
    client, _ = _fake_openai_client(parsed)
    result = extract_candidates("t", ["OpenAI", "CoreWeave"], provider="openai", client=client)
    assert result.candidates[0].unit == "usd_billions"


def test_build_messages_includes_entities_and_text():
    msgs = build_messages("SOME DOC TEXT", ["OpenAI", "CoreWeave"])
    assert msgs[0]["role"] == "system"
    joined = " ".join(m["content"] for m in msgs)
    assert "SOME DOC TEXT" in joined
    assert "OpenAI" in joined


def test_document_extraction_scans_deep_chunks_and_deduplicates(monkeypatch):
    seen: list[str] = []
    candidate = ExtractionResult.model_validate(
        {
            "candidates": [
                {
                    "source_entity": "Amazon",
                    "target_entity": "Anthropic",
                    "relationship_type": "investment_exposure",
                    "metric": "investment",
                    "value": 8.0,
                    "unit": "usd_billions",
                    "period": None,
                    "exact_passage": "DEEP DISCLOSURE",
                    "document_id": "amazon-10k",
                    "permitted_operation": "none",
                    "unsupported_operation": "none",
                    "missing_information": [],
                    "evidence_class": "reported",
                    "confidence_note": "direct disclosure",
                }
            ]
        }
    )

    def fake_extract(text, known_entities, document_id="doc", **kwargs):
        seen.append(text)
        if "DEEP DISCLOSURE" in text:
            return candidate
        return ExtractionResult(candidates=[])

    monkeypatch.setattr(adapter, "extract_candidates", fake_extract)
    result = adapter.extract_document_candidates(
        "A" * 40 + "\n\nDEEP DISCLOSURE\n\nDEEP DISCLOSURE",
        ["Amazon", "Anthropic"],
        document_id="amazon-10k",
        chunk_chars=25,
    )

    assert sum("DEEP DISCLOSURE" in chunk for chunk in seen) == 2
    assert len(result.candidates) == 1
