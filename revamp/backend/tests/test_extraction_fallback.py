from app.extraction.fallback import propose_candidates


def test_emits_candidate_for_passage_with_two_entities_and_value():
    text = "OpenAI committed $11.9 billion to CoreWeave through 2030."
    result = propose_candidates(text, known_entities=["OpenAI", "CoreWeave", "Nvidia"], document_id="s1")

    assert len(result.candidates) == 1
    c = result.candidates[0]
    assert {c.source_entity, c.target_entity} == {"OpenAI", "CoreWeave"}
    assert c.source_entity == "OpenAI"  # first in appearance order
    assert c.value == 11.9
    assert c.unit == "usd_billions"
    assert c.evidence_class == "reported"
    assert c.document_id == "s1"
    # exact_passage must be a verbatim substring of the input
    assert c.exact_passage in text


def test_no_value_yields_unknown_evidence_class():
    text = "OpenAI and CoreWeave have a commercial relationship."
    result = propose_candidates(text, known_entities=["OpenAI", "CoreWeave"])
    assert result.candidates[0].value is None
    assert result.candidates[0].evidence_class == "unknown"


def test_passage_with_one_entity_is_skipped():
    text = "OpenAI reported strong revenue growth this year."
    result = propose_candidates(text, known_entities=["OpenAI", "CoreWeave"])
    assert result.candidates == []


def test_is_deterministic():
    text = "OpenAI committed $11.9 billion to CoreWeave."
    a = propose_candidates(text, ["OpenAI", "CoreWeave"])
    b = propose_candidates(text, ["OpenAI", "CoreWeave"])
    assert a.model_dump() == b.model_dump()
