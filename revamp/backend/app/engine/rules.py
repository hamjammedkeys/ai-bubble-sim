from app.engine.models import EdgeInput, EdgeResult, Shock

_PERCENT_UNITS = {"percent", "ownership_pct", "pct", "%"}
_UNIT_SUFFIX = {"usd_billions": "B", "usd_millions": "M", "usd": ""}


def _money(value: float, unit: str | None) -> str:
    """Render a money amount with a suffix derived from its unit, never assumed.

    Guards the headline number against a 1000x mislabel (e.g. printing a
    usd_millions value with a 'B' suffix)."""
    if unit in _UNIT_SUFFIX:
        return f"${value:.1f}{_UNIT_SUFFIX[unit]}"
    return f"${value:.1f} {unit}" if unit else f"${value:.1f}"


def _ownership_fraction(edge: EdgeInput) -> float:
    value = edge.value or 0.0
    if edge.unit in _PERCENT_UNITS or value > 1:
        return value / 100.0
    return value


def equity_method_rule(edge: EdgeInput, shock: Shock) -> EdgeResult:
    magnitude = shock.magnitude or 0.0
    impact = magnitude * _ownership_fraction(edge)
    return EdgeResult(
        edge_id=edge.id,
        source_entity=edge.source_entity,
        target_entity=edge.target_entity,
        relationship_type=edge.relationship_type,
        kind="impact",
        value=impact,
        unit=shock.unit,
        label=f"{_money(impact, shock.unit)} indicative equity-method impact",
        caveat="Accounting-basis: this is the equity-method share of a disclosed net loss, not a cash loss.",
        realized_loss=None,
        evidence_class="calculated",
        visual_state="solid_red",
    )


def _exposure(edge: EdgeInput, kind_label: str) -> EdgeResult:
    return EdgeResult(
        edge_id=edge.id,
        source_entity=edge.source_entity,
        target_entity=edge.target_entity,
        relationship_type=edge.relationship_type,
        kind="exposure",
        value=edge.value,
        unit=edge.unit,
        label=f"{_money(edge.value, edge.unit)} {kind_label} disclosed" if edge.value is not None else f"{kind_label} disclosed",
        caveat="Exposure-at-risk, not a realized loss: realizing it needs PD/LGD/EAD, which no filing discloses.",
        realized_loss=None,
        evidence_class=edge.evidence_class,
        visual_state="solid_orange",
    )


def exposure_rule(edge: EdgeInput, shock: Shock) -> EdgeResult:
    return _exposure(edge, "contract exposure")


def investment_exposure_rule(edge: EdgeInput, shock: Shock) -> EdgeResult:
    return _exposure(edge, "reported investment exposure")


def unresolved_result(edge: EdgeInput) -> EdgeResult:
    return EdgeResult(
        edge_id=edge.id,
        source_entity=edge.source_entity,
        target_entity=edge.target_entity,
        relationship_type=edge.relationship_type,
        kind="unresolved",
        value=None,
        unit=None,
        label="unknown — assumption required",
        caveat="Documented relationship, but no filing discloses how a shock propagates here, so the engine refuses to invent a number.",
        realized_loss=None,
        evidence_class=edge.evidence_class,
        visual_state="dashed_amber",
    )


STRUCTURAL_RULES = {
    "equity_method": equity_method_rule,
    "customer_concentration": exposure_rule,
    "purchase_obligation": exposure_rule,
    "take_or_pay": exposure_rule,
    "counterparty_credit_exposure": exposure_rule,
    "investment_exposure": investment_exposure_rule,
}

BEHAVIOURAL_TYPES = frozenset(
    {
        "behavioural_response",
        "operational_dependency",
        "supplier_dependency",
        "commercial_spending",
    }
)
