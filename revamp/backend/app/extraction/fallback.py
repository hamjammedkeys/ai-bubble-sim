import re

from app.extraction.schema import CandidateEdge, ExtractionResult
from app.ingestion import split_passages

_VALUE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million)", re.IGNORECASE)


def _parse_value(passage: str) -> tuple[float | None, str | None]:
    m = _VALUE_RE.search(passage)
    if not m:
        return None, None
    number = float(m.group(1).replace(",", ""))
    unit = "usd_billions" if m.group(2).lower() == "billion" else "usd_millions"
    return number, unit


def _entities_in_order(passage: str, known_entities: list[str]) -> list[str]:
    found = [(passage.find(e), e) for e in known_entities if e in passage]
    return [e for _, e in sorted(found)]


def propose_candidates(
    document_text: str, known_entities: list[str], document_id: str = "doc"
) -> ExtractionResult:
    candidates: list[CandidateEdge] = []
    for passage in split_passages(document_text):
        matched = _entities_in_order(passage.text, known_entities)
        if len(matched) < 2:
            continue
        value, unit = _parse_value(passage.text)
        candidates.append(
            CandidateEdge(
                source_entity=matched[0],
                target_entity=matched[1],
                relationship_type="operational_dependency",
                metric="mentioned_relationship",
                value=value,
                unit=unit,
                period=None,
                exact_passage=passage.text,
                document_id=document_id,
                permitted_operation="record the disclosed relationship for human review",
                unsupported_operation="treat as a quantified propagation without evidence",
                missing_information=["propagation"],
                evidence_class="reported" if value is not None else "unknown",
                confidence_note="deterministic keyword proposer (offline fallback)",
            )
        )
    return ExtractionResult(candidates=candidates)
