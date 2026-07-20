from app.config import settings
from app.extraction.fallback import propose_candidates
from app.extraction.schema import ExtractionResult
from app.ingestion import chunk_document

SYSTEM_PROMPT = (
    "You extract structured financial-relationship claims from filings. You never "
    "estimate, infer, or calculate a number that is not explicitly stated in the passage "
    "you cite. exact_passage must be copied verbatim from the provided document text — if "
    "you cannot find a verbatim supporting passage, do not emit the candidate. Every "
    "relationship must map to exactly one relationship_type from the provided enum. Set "
    'evidence_class to "calculated" only if every input number is itself quoted in '
    "exact_passage, and show the operation in permitted_operation. Never propose a "
    "behavioural_response edge with a value — those must have value null and evidence_class "
    '"unknown" unless the filing explicitly states an elasticity or ratio. The `unit` field '
    "MUST be exactly one of: usd_billions, usd_millions, usd, percent, ownership_pct, "
    "shares, or null — never free text like '$11.9 billion' or '%'. When uncertain, "
    "prefer fewer, well-evidenced candidates over many speculative ones."
)

# The model sometimes returns natural-language units; normalize to the verifier's
# canonical set so genuinely-cited candidates aren't flagged for the unit alone.
_UNIT_ALIASES = {
    "usd_billions": "usd_billions", "billion usd": "usd_billions", "usd billion": "usd_billions",
    "billions of usd": "usd_billions", "billion": "usd_billions", "$b": "usd_billions", "bn": "usd_billions",
    "usd_millions": "usd_millions", "million usd": "usd_millions", "usd million": "usd_millions",
    "millions of usd": "usd_millions", "million": "usd_millions", "$m": "usd_millions", "mm": "usd_millions",
    "percent": "percent", "%": "percent", "pct": "percent", "percentage": "percent",
    "ownership_pct": "ownership_pct", "usd": "usd", "$": "usd", "shares": "shares",
}


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return _UNIT_ALIASES.get(unit.strip().lower(), unit)


def build_messages(document_text: str, known_entities: list[str]) -> list[dict]:
    entities = ", ".join(known_entities) if known_entities else "(none provided)"
    user = (
        f"Known entities: {entities}\n\n"
        f"Extract candidate relationship edges from this document text:\n\n{document_text}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _extract_openai(
    document_text: str, known_entities: list[str], document_id: str, client=None
) -> ExtractionResult:
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
    # Use the SDK's native Pydantic parsing: it derives an OpenAI-strict JSON
    # schema from ExtractionResult (additionalProperties:false, all fields
    # required) and returns a parsed model instance — avoiding the hand-rolled
    # response_format that OpenAI strict mode rejects.
    completion = client.beta.chat.completions.parse(
        model=settings.openai_model,
        temperature=0,
        messages=build_messages(document_text, known_entities),
        response_format=ExtractionResult,
    )
    result = completion.choices[0].message.parsed
    if result is None:
        return ExtractionResult(candidates=[])
    # The caller's document_id is authoritative, not whatever the model echoed;
    # units are normalized to the verifier's canonical vocabulary.
    return ExtractionResult(
        candidates=[
            c.model_copy(update={"document_id": document_id, "unit": _normalize_unit(c.unit)})
            for c in result.candidates
        ]
    )


def extract_candidates(
    document_text: str,
    known_entities: list[str],
    document_id: str = "doc",
    *,
    client=None,
    provider: str | None = None,
) -> ExtractionResult:
    provider = provider or settings.llm_provider
    if provider == "fallback":
        return propose_candidates(document_text, known_entities, document_id)
    if provider == "openai":
        return _extract_openai(document_text, known_entities, document_id, client=client)
    raise ValueError(f"unknown LLM provider: {provider}")


def extract_document_candidates(
    document_text: str,
    known_entities: list[str],
    document_id: str = "doc",
    *,
    client=None,
    provider: str | None = None,
    chunk_chars: int = 30_000,
) -> ExtractionResult:
    """Extract and merge candidates from every bounded document chunk."""
    candidates = []
    seen: set[tuple] = set()
    for chunk in chunk_document(document_text, max_chars=chunk_chars):
        result = extract_candidates(
            chunk,
            known_entities,
            document_id=document_id,
            client=client,
            provider=provider,
        )
        for candidate in result.candidates:
            key = (
                candidate.source_entity,
                candidate.target_entity,
                candidate.relationship_type,
                candidate.metric,
                candidate.value,
                candidate.unit,
                candidate.period,
                candidate.permitted_operation,
                candidate.unsupported_operation,
                tuple(candidate.missing_information),
                candidate.evidence_class,
            )
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
    return ExtractionResult(candidates=candidates)
