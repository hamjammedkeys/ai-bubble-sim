import re

from fragility_map.extraction.candidates import RelationshipCandidateV2

_SENTENCE = re.compile(r"(?:[^.]|\.(?=\d))+\.")
_BILLION = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)\s*billion", re.IGNORECASE)
_PERCENT = re.compile(r"([0-9]+(?:\.[0-9]+)?)%\s+of\s+(?:our\s+)?revenue", re.IGNORECASE)


def _sentences(text: str) -> list[str]:
    return [match.group(0).strip() for match in _SENTENCE.finditer(text)]


class KeywordProposer:
    """Deterministic, network-free proposer. The seam where an LLM adapter can later
    be swapped in behind the RelationshipProposer protocol."""

    def __init__(
        self, source_accession: str, source_company_id: str, target_company_id: str
    ) -> None:
        self._accession = source_accession
        self._source_company_id = source_company_id
        self._target_company_id = target_company_id

    def _base(self, source_id: str, relationship_type: str, quoted_text: str) -> dict:
        return {
            "candidate_id": f"{source_id}-{relationship_type}",
            "source_id": source_id,
            "source_accession": self._accession,
            "source_company_id": self._source_company_id,
            "target_company_id": self._target_company_id,
            "relationship_type": relationship_type,
            "quoted_text": quoted_text,
        }

    def propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]:
        candidates: list[RelationshipCandidateV2] = []
        for sentence in _sentences(filing_text):
            billion = _BILLION.search(sentence)
            if billion is not None:
                token = billion.group(0)
                value = float(billion.group(1)) * 1_000
                candidates.append(
                    RelationshipCandidateV2(
                        **self._base(source_id, "take_or_pay", sentence),
                        numeric_token=token,
                        value=value,
                        unit="USD",
                        period="through 2030" if "2030" in sentence else None,
                        supported_rule="disclosed purchase-commitment envelope",
                        unsupported_inference=(
                            "the full envelope becomes a realized loss on distress"
                        ),
                    )
                )
                continue
            percent = _PERCENT.search(sentence)
            if percent is not None:
                candidates.append(
                    RelationshipCandidateV2(
                        **self._base(source_id, "customer_concentration", sentence),
                        numeric_token=f"{percent.group(1)}%",
                        value=float(percent.group(1)) / 100,
                        unit=None,
                        period=None,
                        supported_rule="disclosed customer-concentration percentage",
                        unsupported_inference=(
                            "the buyer's own revenue drives this counterparty's purchases"
                        ),
                    )
                )
        return candidates
