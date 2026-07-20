import re

from rapidfuzz import fuzz

from app.extraction.schema import CandidateEdge

ALLOWED_UNITS: set[str | None] = {
    "usd_billions",
    "usd_millions",
    "usd",
    "percent",
    "shares",
    "ownership_pct",
    None,
}

_PASSAGE_MATCH_THRESHOLD = 92


def _value_forms(value: float) -> list[str]:
    """String forms of a number to search for in a passage."""
    forms = {str(value), f"{value:.1f}", f"{value:,.1f}"}
    if value == int(value):
        forms.add(str(int(value)))
        forms.add(f"{int(value):,}")
    return [f for f in forms if f]


def _value_in_text(value: float, text: str) -> bool:
    for form in _value_forms(value):
        # The form must not be embedded in a longer number (no adjacent digit
        # or decimal point on either side), so "1" does not match inside "15%".
        if re.search(rf"(?<![\d.]){re.escape(form)}(?![\d.])", text):
            return True
    return False


def verify_candidate(candidate: CandidateEdge, document_text: str, document_exists: bool) -> dict:
    score = fuzz.partial_ratio(candidate.exact_passage, document_text)
    passage_found = score >= _PASSAGE_MATCH_THRESHOLD

    if candidate.value is None:
        number_found: bool | None = None
    else:
        number_found = _value_in_text(candidate.value, candidate.exact_passage)

    entities_found = (
        candidate.source_entity in candidate.exact_passage
        and candidate.target_entity in candidate.exact_passage
    )
    unit_allowed = candidate.unit in ALLOWED_UNITS

    # Arithmetic re-derivation is only defined when the candidate claims a calculation.
    # Without the quoted input operands we cannot re-derive here, so we do not assert it
    # as a hard pass/fail: report None (not applicable) rather than fabricate a verdict.
    arithmetic_ok: bool | None = None

    hard_checks = [passage_found, entities_found, unit_allowed, document_exists]
    if number_found is not None:
        hard_checks.append(number_found)

    return {
        "passage_found": passage_found,
        "match_score": round(float(score), 1),
        "number_found": number_found,
        "entities_found": entities_found,
        "unit_allowed": unit_allowed,
        "arithmetic_ok": arithmetic_ok,
        "source_valid": document_exists,
        "overall": "pass" if all(hard_checks) else "flag",
    }
