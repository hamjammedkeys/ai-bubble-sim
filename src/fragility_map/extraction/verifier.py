import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from fragility_map.extraction.candidates import RelationshipCandidateV2


@dataclass(frozen=True)
class SourceManifestEntry:
    accession: str
    source_id: str
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    candidate_id: str
    checks: tuple[VerificationCheck, ...]
    semantic_interpretation: str
    mechanically_valid: bool


_ALIASES = {"msft": ("msft", "microsoft"), "coreweave": ("coreweave",)}


def _check(name: str, passed: bool, detail: str) -> VerificationCheck:
    return VerificationCheck(name, passed, detail)


def _arithmetic(candidate: RelationshipCandidateV2) -> VerificationCheck:
    if candidate.numeric_token is None or candidate.value is None:
        return _check("arithmetic", True, "not applicable")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", candidate.numeric_token)
    if match is None:
        return _check("arithmetic", False, "numeric token has no number")
    number = float(match.group(1))
    token = candidate.numeric_token.lower()
    if "billion" in token:
        number *= 1_000_000_000
    elif "million" in token:
        number *= 1_000_000
    passed = abs(number - candidate.value) < max(0.01, abs(candidate.value) * 1e-6)
    return _check("arithmetic", passed, f"token={number:g}, value={candidate.value:g}")


def verify_candidate(
    filing_text: str,
    candidate: RelationshipCandidateV2,
    source_manifest: Sequence[SourceManifestEntry],
    superseded_accessions: Collection[str] = (),
) -> VerificationResult:
    lowered = filing_text.lower()
    source_aliases = _ALIASES.get(candidate.source_company_id, (candidate.source_company_id,))
    target_aliases = _ALIASES.get(
        candidate.target_company_id or "", (candidate.target_company_id or "",)
    )
    source_ok = any(alias in lowered for alias in source_aliases)
    target_ok = candidate.target_company_id is None or any(
        alias in lowered for alias in target_aliases
    )
    period_ok = candidate.period is None or candidate.period.lower() in lowered
    unit_ok = (
        candidate.unit is None
        or candidate.unit.lower() in lowered
        or (candidate.unit.upper() == "USD" and "$" in filing_text)
    )
    accession_ok = any(
        e.accession == candidate.source_accession and e.source_id == candidate.source_id
        for e in source_manifest
    )
    checks = (
        _check("quoted_text", candidate.quoted_text in filing_text, "quote present"),
        _check(
            "numeric_token",
            candidate.numeric_token is None or candidate.numeric_token.lower() in lowered,
            "token present",
        ),
        _check("entities", source_ok and target_ok, "entities present"),
        _check("period", period_ok, "period present"),
        _check("unit", unit_ok, "unit present"),
        _arithmetic(candidate),
        _check("accession", accession_ok, "accession resolved"),
        _check(
            "supersession",
            candidate.source_accession not in superseded_accessions,
            "not superseded",
        ),
    )
    return VerificationResult(
        candidate.candidate_id, checks, "pending_human_review", all(c.passed for c in checks)
    )
