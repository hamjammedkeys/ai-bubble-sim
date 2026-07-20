from app.chat.filing_search import query_terms, rank_passages

FILING = (
    "Item 1. Business.\nThe Company designs cloud infrastructure.\n\n"
    "Item 1A. Risk Factors.\nOur business depends on a small number of large customers. "
    "The loss of a major customer could materially harm our revenue and results of operations. "
    "We also face significant competition and supply-chain concentration risk.\n\n"
    "Item 7. Management's Discussion.\nRevenue grew 40% year over year driven by AI demand.\n"
)


def test_query_terms_drops_filler_keeps_domain_words():
    terms = query_terms("what are the main risk factors?")
    assert "risk" in terms and "factors" in terms and "main" in terms
    assert "the" not in terms and "what" not in terms


def test_rank_passages_finds_the_relevant_section():
    hits = rank_passages(FILING, "risk factors")
    assert hits, "expected at least one passage"
    assert "Risk Factors" in hits[0]["snippet"]
    assert set(hits[0]["matched_terms"]) == {"risk", "factors"}


def test_rank_passages_prefers_more_distinct_terms():
    hits = rank_passages(FILING, "customer concentration risk revenue")
    # The risk-factors paragraph matches several distinct query terms; it should win.
    assert "customer" in hits[0]["snippet"].lower()


def test_rank_passages_empty_when_nothing_matches():
    assert rank_passages(FILING, "cryptocurrency mining") == []


def test_rank_passages_snippet_is_truncated_for_long_blocks():
    block = "irrelevant filler. " * 400 + "the disclosed goodwill impairment was material."
    hits = rank_passages(block, "goodwill impairment")
    assert hits
    assert len(hits[0]["snippet"]) <= 720
    assert "impairment" in hits[0]["snippet"].lower()
