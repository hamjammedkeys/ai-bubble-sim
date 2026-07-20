"""Keyword passage retrieval over ingested filing text.

The copilot uses this to answer free-form questions about a filing's *content*
(e.g. "what are the risk factors?") by pulling the most relevant passages out of
the stored `raw_text` and handing them to the model to quote and cite. It stays
deliberately simple — token-overlap scoring, no embeddings, no new dependency —
which is sufficient for filings of tens of thousands of characters and keeps the
retrieval auditable (the model only ever sees text that is verifiably in the
document).
"""

import re

# Only structural filler is dropped. Domain words a user is likely to search for
# ("risk", "factors", "revenue"...) are intentionally NOT stopped.
_STOP = frozenset(
    {
        "the", "a", "an", "of", "and", "or", "to", "in", "for", "on", "is", "are",
        "what", "how", "does", "did", "do", "which", "that", "this", "with", "by",
        "at", "as", "it", "its", "their", "was", "were", "be", "about", "tell",
        "me", "you", "please", "any", "there", "has", "have", "had", "from",
    }
)


def query_terms(query: str) -> list[str]:
    """Distinct, lower-cased content tokens from a natural-language query."""
    seen: dict[str, None] = {}
    for token in re.findall(r"[a-z0-9]+", query.lower()):
        if len(token) >= 2 and token not in _STOP:
            seen.setdefault(token, None)
    return list(seen)


def _blocks(text: str, *, window: int = 800, overlap: int = 200) -> list[str]:
    """Split text into candidate passages, splitting over-long paragraphs.

    Paragraphs are delimited by blank lines so a section heading stays attached
    to the prose beneath it (filings put "Item 1A. Risk Factors." on its own line
    above the text it introduces).
    """
    blocks: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= window + overlap:
            blocks.append(para)
            continue
        step = window
        for start in range(0, len(para), step):
            blocks.append(para[start : start + window + overlap])
    return blocks


def _snippet(block: str, terms: list[str], *, max_len: int = 700) -> str:
    """A window of the block centred on the first matched term."""
    if len(block) <= max_len:
        return block
    lower = block.lower()
    first = min(
        (idx for idx in (lower.find(t) for t in terms) if idx >= 0),
        default=0,
    )
    start = max(0, first - 120)
    end = min(len(block), start + max_len)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(block) else ""
    return f"{prefix}{block[start:end].strip()}{suffix}"


def rank_passages(raw_text: str, query: str, *, limit: int = 5) -> list[dict]:
    """Return the top passages of `raw_text` for `query`, best first.

    Each item is ``{"snippet": str, "score": int, "matched_terms": [str]}``.
    Score prioritises passages matching many *distinct* query terms, then total
    occurrences — so a paragraph mentioning several of the asked-about words
    outranks one that merely repeats a single common word.
    """
    terms = query_terms(query)
    if not terms or not raw_text:
        return []

    scored: list[tuple[int, int, list[str], str]] = []
    for order, block in enumerate(_blocks(raw_text)):
        lower = block.lower()
        matched = [t for t in terms if t in lower]
        if not matched:
            continue
        total = sum(lower.count(t) for t in matched)
        score = len(matched) * 1000 + total
        scored.append((score, -order, matched, block))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [
        {"snippet": _snippet(block, matched), "score": score, "matched_terms": matched}
        for score, _order, matched, block in scored[:limit]
    ]
