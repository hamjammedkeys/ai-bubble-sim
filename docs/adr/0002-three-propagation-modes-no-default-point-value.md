# ADR 0002 — Three propagation modes; assumed multipliers get no default point value

Status: Accepted

## Context

Even with per-axis evidence labels (ADR 0001), the propagation engine still multiplies by
a *number*. The failure mode: an edge whose Propagation axis is `Assumed` gets quietly
assigned a point multiplier (say 0.7), propagated at full strength, and printed as a
precise "−18%" on the leaderboard — making the honesty cosmetic (the label sits in a
tooltip while the false-precision number drives the ranking).

## Decision

**An assumed multiplier never receives a default point value in the evidence-backed run.**
It becomes an uncertain parameter, and the engine separates what the *evidence* implies
from what is only true under a *chosen scenario*. Three legitimate modes:

Take `OpenAI → Azure`, 30% OpenAI revenue shock, `Impact = −30% × Exposure × β`, where the
evidence constrains `Exposure ∈ [0.4, 0.6]` but nothing constrains the elasticity `β`:

1. **Evidence-only mode** — the shock *stops* at the unconstrained edge. Output:
   "Not identifiable from available evidence" (this is *not* an impact of zero — it is the
   absence of an evidence-backed number).

2. **Scenario mode** — the user explicitly supplies `β ∈ [0.3, 0.8]`; the engine returns
   the conditional interval `−30% × [0.4,0.6] × [0.3,0.8] = [−3.6%, −14.4%]`, and the UI
   must present it *conditional on the user-selected elasticity* — never headlined as a
   single −9%.

3. **Sensitivity mode** — output shown as a function of the unknown, plus the decision
   threshold (e.g. "Azure exceeds 10% impact only if β ⪆ 0.56–0.83, depending on
   exposure"). The threshold is often more useful than an invented forecast.

## Consequences

- No hidden defaults: the engine must refuse to fabricate a point value for an
  unconstrained multiplier.
- Every propagated number carries its mode; a bare percentage with no mode is a bug.
- **Open tension for the next grill:** evidence-only mode makes a multi-hop ripple *die*
  at the first unconstrained hop — which collides with the demo's hero "ripple across the
  network" animation. Which mode is the default the judge sees first is unresolved.
