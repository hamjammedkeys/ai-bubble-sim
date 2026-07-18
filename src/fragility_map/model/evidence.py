from dataclasses import dataclass
from enum import StrEnum


class ProvenanceLabel(StrEnum):
    REPORTED = "reported"
    CALCULATED = "calculated"
    CONSTRAINED = "constrained_estimate"
    ASSUMED = "assumed"
    HYPOTHETICAL = "hypothetical"


class StructureType(StrEnum):
    EQUITY_METHOD = "equity_method"
    TAKE_OR_PAY = "take_or_pay"
    CUSTOMER_CONCENTRATION = "customer_concentration"
    PURCHASE_OBLIGATION = "purchase_obligation"
    OWNERSHIP_STAKE = "ownership_stake"
    DEBT_OBLIGATION = "debt_obligation"
    BEHAVIOURAL = "behavioural"


class Tier(StrEnum):
    SOLID_RED = "solid_red"
    SOLID_ORANGE = "solid_orange"
    DASHED_AMBER = "dashed_amber"
    DIFFUSE_AMBER = "diffuse_amber"


@dataclass(frozen=True)
class EdgeProvenance:
    relationship: ProvenanceLabel
    magnitude: ProvenanceLabel
    propagation: ProvenanceLabel
    timing: ProvenanceLabel


def quantifies_propagation(prov: EdgeProvenance) -> bool:
    return prov.propagation in {ProvenanceLabel.REPORTED, ProvenanceLabel.CALCULATED}
