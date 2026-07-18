import re

from pydantic import BaseModel, Field


class RelationshipCandidate(BaseModel):
    company_id: str
    source_id: str
    evidence_type: str
    extracted_text: str
    parser_method: str
    confidence: float = Field(ge=0.0, le=1.0)
    percentage: float | None = None
    amount: float | None = None


def estimate_confidence(evidence_type: str, has_numeric_value: bool) -> float:
    if evidence_type == "exact_amount" and has_numeric_value:
        return 1.0
    if evidence_type == "customer_concentration" and has_numeric_value:
        return 0.9
    if evidence_type == "relationship_disclosure" and has_numeric_value:
        return 0.6
    return 0.3


def _parse_money_amount(text: str) -> float | None:
    match = re.search(r"\$([0-9]+(?:\.[0-9]+)?)\s*(billion|million)", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    scale = 1_000_000_000 if match.group(2).lower() == "billion" else 1_000_000
    return value * scale


def _parse_percentage(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)%\s+of\s+(?:total\s+)?revenue", text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1)) / 100


def extract_relationship_candidates(
    company_id: str,
    source_id: str,
    text: str,
) -> list[RelationshipCandidate]:
    normalized = " ".join(text.split())
    candidates: list[RelationshipCandidate] = []
    if "customer" in normalized.lower() and "revenue" in normalized.lower():
        percentage = _parse_percentage(normalized)
        candidates.append(
            RelationshipCandidate(
                company_id=company_id,
                source_id=source_id,
                evidence_type="customer_concentration",
                extracted_text=normalized,
                parser_method="regex_customer_revenue_percentage",
                confidence=estimate_confidence("customer_concentration", percentage is not None),
                percentage=percentage,
            )
        )
    if "purchase commitments" in normalized.lower():
        amount = _parse_money_amount(normalized)
        candidates.append(
            RelationshipCandidate(
                company_id=company_id,
                source_id=source_id,
                evidence_type="purchase_commitment",
                extracted_text=normalized,
                parser_method="regex_purchase_commitment_amount",
                confidence=estimate_confidence("exact_amount", amount is not None),
                amount=amount,
            )
        )
    return candidates
