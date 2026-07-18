"""Stable JSON serialization for evidence-honest compound shock results."""

from collections.abc import Mapping, Sequence

from fragility_map.extraction.candidates import RelationshipCandidateV2
from fragility_map.model.evidence import Tier
from fragility_map.model.propagation import (
    ShockResult,
    StructuralRelationship,
    rank_vulnerability,
)
from fragility_map.model.stress import CompanyFinancials

_SCENARIO_LANGUAGE = (
    "calculated Impact plus activated Exposure; downstream loss not identifiable"
)


def _provenance_payload(relationship: StructuralRelationship) -> dict[str, str]:
    provenance = relationship.provenance
    return {
        "relationship": provenance.relationship.value,
        "magnitude": provenance.magnitude.value,
        "propagation": provenance.propagation.value,
        "timing": provenance.timing.value,
    }


def _candidate_payload(candidate: RelationshipCandidateV2) -> dict[str, object]:
    return {
        "candidateId": candidate.candidate_id,
        "sourceId": candidate.source_id,
        "sourceAccession": candidate.source_accession,
        "sourceCompanyId": candidate.source_company_id,
        "targetCompanyId": candidate.target_company_id,
        "relationshipType": candidate.relationship_type,
        "quotedText": candidate.quoted_text,
        "numericToken": candidate.numeric_token,
        "value": candidate.value,
        "unit": candidate.unit,
        "period": candidate.period,
        "supportedRule": candidate.supported_rule,
        "unsupportedInference": candidate.unsupported_inference,
        "status": candidate.status.value,
    }


def build_evidence_payload(
    companies: Mapping[str, CompanyFinancials],
    relationships: Sequence[StructuralRelationship],
    shock_result: ShockResult,
    candidates: Sequence[RelationshipCandidateV2] = (),
    include_realized_loss_guardrail: bool = False,
) -> dict[str, object]:
    """Serialize only activated results, preserving their evidence and epistemic limits."""
    relationship_by_id = {
        relationship.relationship_id: relationship for relationship in relationships
    }
    tiers_by_target: dict[str, list[str]] = {}
    displayed_edges = [
        edge
        for edge in shock_result.edges
        if include_realized_loss_guardrail or edge.tier is not Tier.DASHED_AMBER
    ]
    for edge in displayed_edges:
        tiers_by_target.setdefault(edge.target_company_id, []).append(edge.tier.value)

    nodes: list[dict[str, object]] = []
    for node in shock_result.nodes.values():
        company = companies.get(node.company_id)
        ranking_eligible = (
            node.epistemic_state == "quantified_impact" and node.quantified_impact is not None
        )
        nodes.append(
            {
                "companyId": node.company_id,
                "label": company.name if company is not None else node.company_id,
                "quantifiedImpact": node.quantified_impact,
                "activatedExposure": node.activated_exposure,
                "epistemicState": node.epistemic_state,
                "rankingEligible": ranking_eligible,
                "tierSummary": sorted(set(tiers_by_target.get(node.company_id, []))),
            }
        )

    edges: list[dict[str, object]] = []
    for edge in displayed_edges:
        relationship = relationship_by_id.get(edge.relationship_id)
        if relationship is None and edge.tier is Tier.DASHED_AMBER:
            relationship = relationship_by_id.get(
                edge.relationship_id.removesuffix("-realized-loss")
            )
        if relationship is None:
            continue
        edges.append(
            {
                "relationshipId": edge.relationship_id,
                "source": edge.source_company_id,
                "target": edge.target_company_id,
                "structureType": relationship.structure_type.value,
                "tier": edge.tier.value,
                "resultKind": edge.result_kind,
                "value": edge.value,
                "basis": edge.basis,
                "provenance": _provenance_payload(relationship),
                "sourceAccession": relationship.source_accession,
                "evidenceQuote": relationship.evidence_quote,
                "sourceLocation": relationship.source_location,
            }
        )

    shock = shock_result.shock
    return {
        "scenario": {
            "incrementalGaapLoss": shock.incremental_gaap_loss if shock is not None else None,
            "creditStatus": shock.credit_status if shock is not None else None,
            "defaultStatus": shock.default_status if shock is not None else None,
            "language": _SCENARIO_LANGUAGE,
        },
        "nodes": nodes,
        "edges": edges,
        "reviewCandidates": [_candidate_payload(candidate) for candidate in candidates],
        "auditLog": [],
        "ranking": [
            {"companyId": company_id, "magnitude": magnitude}
            for company_id, magnitude in rank_vulnerability(shock_result)
        ],
    }
