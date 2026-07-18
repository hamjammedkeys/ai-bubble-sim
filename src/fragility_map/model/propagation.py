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
        if rel.structure_type == StructureType.EQUITY_METHOD:
            if shock.incremental_gaap_loss is None or not quantifies_propagation(
                rel.provenance
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
            nodes[rel.target_company_id] = NodeResult(
                rel.target_company_id,
                quantified_impact=round(value, 6),
                activated_exposure=None,
                epistemic_state="quantified_impact",
            )

    return ShockResult(edges=edges, nodes=nodes)
