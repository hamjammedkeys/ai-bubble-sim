"""Verified, immutable source evidence for the compound-credit-event hero."""

from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, StructureType
from fragility_map.model.propagation import Shock, StructuralRelationship
from fragility_map.model.stress import CompanyFinancials


def _reported_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.CONSTRAINED,
    )


def hero_companies() -> dict[str, CompanyFinancials]:
    """Return the companies named by the hero's evidenced structural relationships."""
    return {
        "openai": CompanyFinancials(
            "openai", "OpenAI", "ai_model_provider", 0.0, 0.0, 0.0, 0.0, 0.0
        ),
        "msft": CompanyFinancials(
            "msft", "Microsoft", "cloud_platform", 0.0, 0.0, 0.0, 0.0, 0.0
        ),
        "coreweave": CompanyFinancials(
            "coreweave", "CoreWeave", "cloud_infrastructure", 0.0, 0.0, 0.0, 0.0, 0.0
        ),
        "nvda": CompanyFinancials(
            "nvda", "NVIDIA", "semiconductor", 0.0, 0.0, 0.0, 0.0, 0.0
        ),
    }


def hero_relationships() -> list[StructuralRelationship]:
    """Return only the disclosed structural links used by the hero scenario."""
    return [
        StructuralRelationship(
            "openai-msft",
            "openai",
            "msft",
            StructureType.EQUITY_METHOD,
            _reported_provenance(),
            ownership_share=0.27,
            source_accession="0001193125-25-256321",
            evidence_quote=(
                "As a result of the recapitalization, Microsoft holds approximately 27 "
                "percent in the PBC on an as-converted diluted basis."
            ),
            source_location="Microsoft Form 10-Q, Note 17 — Subsequent Event (2025-09-30)",
        ),
        StructuralRelationship(
            "openai-coreweave",
            "openai",
            "coreweave",
            StructureType.TAKE_OR_PAY,
            _reported_provenance(),
            committed_envelope=11_900_000_000,
            source_accession="0001193125-25-058309",
            evidence_quote=(
                "As of March 11, 2025, subject to any termination described below and "
                "satisfaction of delivery and availability of service requirements, OpenAI "
                "has committed to pay us up to approximately $11.9 billion through October 2030."
            ),
            source_location="CoreWeave Form S-1/A, Note 18 — Subsequent Events (2025-03-20)",
        ),
        StructuralRelationship(
            "coreweave-nvda",
            "coreweave",
            "nvda",
            StructureType.BEHAVIOURAL,
            _reported_provenance(),
            source_accession="0001193125-25-058309",
        ),
    ]


def hero_shock() -> Shock:
    """Return the explicit observed state for the compound-credit-event hero."""
    return Shock("openai", 10_000_000_000, "severe_distress", "not_defaulted")
