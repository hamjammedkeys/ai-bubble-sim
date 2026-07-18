from dataclasses import dataclass

from fragility_map.model.evidence import (
    EdgeProvenance,
    StructureType,
    Tier,
    quantifies_propagation,
)


@dataclass(frozen=True)
class Shock:
    source_company_id: str
    incremental_gaap_loss: float | None = None
    credit_status: str = "normal"
    default_status: str = "not_defaulted"


@dataclass(frozen=True)
class EdgeFlowShock:
    relationship_id: str
    flow_change: float


@dataclass(frozen=True)
class StructuralRelationship:
    relationship_id: str
    source_company_id: str
    target_company_id: str
    structure_type: StructureType
    provenance: EdgeProvenance
    ownership_share: float | None = None
    concentration: float | None = None
    committed_envelope: float | None = None
    source_accession: str | None = None


@dataclass(frozen=True)
class EdgeResult:
    relationship_id: str
    source_company_id: str
    target_company_id: str
    tier: Tier
    result_kind: str
    value: float | None
    basis: str


@dataclass(frozen=True)
class NodeResult:
    company_id: str
    quantified_impact: float | None
    activated_exposure: float | None
    epistemic_state: str


@dataclass(frozen=True)
class ShockResult:
    edges: list[EdgeResult]
    nodes: dict[str, NodeResult]


def run_compound_shock(
    relationships: list[StructuralRelationship],
    shock: Shock,
) -> ShockResult:
    edges: list[EdgeResult] = []
    nodes: dict[str, NodeResult] = {}

    for rel in relationships:
        if rel.source_company_id != shock.source_company_id:
            continue
        if rel.structure_type == StructureType.CUSTOMER_CONCENTRATION:
            # Guardrail (ADR 0004): concentration only quantifies under an edge-flow shock.
            continue
        if rel.structure_type == StructureType.BEHAVIOURAL or not quantifies_propagation(
            rel.provenance
        ):
            edges.append(
                EdgeResult(
                    rel.relationship_id,
                    rel.source_company_id,
                    rel.target_company_id,
                    Tier.DIFFUSE_AMBER,
                    "behavioural",
                    None,
                    "documented dependency; magnitude not identifiable from evidence",
                )
            )
            if rel.target_company_id not in nodes:
                nodes[rel.target_company_id] = NodeResult(
                    rel.target_company_id,
                    quantified_impact=None,
                    activated_exposure=None,
                    epistemic_state="not_identifiable",
                )
            continue
        if rel.structure_type == StructureType.EQUITY_METHOD:
            if (
                shock.incremental_gaap_loss is None
                or rel.ownership_share is None
            ):
                continue
            value = -(rel.ownership_share * shock.incremental_gaap_loss)
            edges.append(
                EdgeResult(
                    rel.relationship_id,
                    rel.source_company_id,
                    rel.target_company_id,
                    Tier.SOLID_RED,
                    "impact",
                    round(value, 6),
                    "equity-method share of stated GAAP loss",
                )
            )
            existing = nodes.get(rel.target_company_id)
            rounded_value = round(value, 6)
            existing_impact = existing.quantified_impact if existing else None
            impact = round((existing_impact or 0.0) + rounded_value, 6)
            exposure = existing.activated_exposure if existing else None
            nodes[rel.target_company_id] = NodeResult(
                rel.target_company_id,
                quantified_impact=impact,
                activated_exposure=exposure,
                epistemic_state="quantified_impact",
            )
        elif rel.structure_type == StructureType.TAKE_OR_PAY:
            distressed = (
                shock.credit_status == "severe_distress"
                or shock.default_status == "defaulted"
            )
            if (
                not distressed
                or rel.committed_envelope is None
            ):
                continue
            edges.append(
                EdgeResult(
                    rel.relationship_id,
                    rel.source_company_id,
                    rel.target_company_id,
                    Tier.SOLID_ORANGE,
                    "exposure",
                    rel.committed_envelope,
                    "take-or-pay contract envelope activated (not a realized loss)",
                )
            )
            existing = nodes.get(rel.target_company_id)
            impact = existing.quantified_impact if existing else None
            existing_exposure = existing.activated_exposure if existing else None
            exposure = rel.committed_envelope
            if existing_exposure is not None:
                exposure = existing_exposure + (exposure or 0.0)
            nodes[rel.target_company_id] = NodeResult(
                rel.target_company_id,
                quantified_impact=impact,
                activated_exposure=exposure,
                epistemic_state=(
                    "quantified_impact" if impact is not None else "exposure_detected"
                ),
            )

    return ShockResult(edges=edges, nodes=nodes)


def run_edge_flow_shock(
    relationships: list[StructuralRelationship],
    shock: EdgeFlowShock,
) -> ShockResult:
    edges: list[EdgeResult] = []
    nodes: dict[str, NodeResult] = {}
    for rel in relationships:
        if rel.relationship_id != shock.relationship_id:
            continue
        if rel.structure_type != StructureType.CUSTOMER_CONCENTRATION:
            continue
        if rel.concentration is None or not quantifies_propagation(rel.provenance):
            continue
        value = round(rel.concentration * shock.flow_change, 6)
        edges.append(
            EdgeResult(
                rel.relationship_id,
                rel.source_company_id,
                rel.target_company_id,
                Tier.SOLID_ORANGE,
                "exposure",
                value,
                "disclosed customer-concentration exposure to an edge-flow change",
            )
        )
        nodes[rel.target_company_id] = NodeResult(
            rel.target_company_id,
            quantified_impact=None,
            activated_exposure=value,
            epistemic_state="exposure_detected",
        )
    return ShockResult(edges=edges, nodes=nodes)


def rank_vulnerability(result: ShockResult) -> list[tuple[str, float]]:
    ranked = [
        (node.company_id, abs(node.quantified_impact))
        for node in result.nodes.values()
        if node.epistemic_state == "quantified_impact"
        and node.quantified_impact is not None
    ]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked
