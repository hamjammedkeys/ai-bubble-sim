# ADR 0004 — Solid structural core, amber behavioural periphery

Status: Accepted (resolves the reframe left open in ADR 0003)

## Context

ADR 0003's assumption — that a *behavioural* solid-red hop exists — is broken (Q5). No
filing constrains a revenue→spending / capex→orders elasticity. But shocks that travel by
**disclosed financial structure** (accounting rules, contracts, concentration ratios) are
sourced and deterministic. The quantified layer relocates there.

## Decision

**The engine's quantified (solid-red) layer is structural propagation; behaviour is always
the amber dissolve.** Structural edges produce *different mathematical objects* and must
not all be labelled "predicted revenue impact":

| Structure | What it produces |
|---|---|
| Equity method | Accounting income impact |
| Customer concentration | Direct-exposure bound |
| Take-or-pay contract | Revenue floor / protected amount |
| Purchase obligation | Minimum future cash outflow |
| Ownership stake | Gain/loss participation |
| Debt obligation | Fixed payment schedule |

### The three solid edges of the hero graph

1. **OpenAI → Microsoft (equity method).** MSFT FY2025 AR: $13B funding commitments,
   equity-method accounting; ~27% as-converted ownership post-recap; FY2026 Q1 OpenAI
   losses cut MSFT net income by $3.1B. Rule ≈ `ΔIncome_MSFT ≈ OwnershipShare ×
   ΔNetAssets_OpenAI`, allowing accounting adjustments/lag. Runs **OpenAI → Microsoft**
   (upstream), not the buyer-shock direction.

2. **Microsoft → CoreWeave (concentration).** CoreWeave S-1/A: MSFT = 35% (2023), 62%
   (2024) of revenue; top-2 = 77% (2024). A shock **"MSFT purchases from CoreWeave −20%"**
   → `62% × −20% = −12.4%` first-order, solid. A shock **"MSFT earnings −20%"** is **amber**
   — the filing does not link MSFT earnings to MSFT's CoreWeave purchases. The engine MUST
   enforce this: a shock to the disclosed *edge flow* is solid; a shock to an upstream
   *financial aggregate* that only reaches the edge via behaviour is amber.

3. **OpenAI → CoreWeave (take-or-pay).** CoreWeave S-1/A: $15.1B remaining performance
   obligations (end-2024); up to $11.55B future revenue under the OpenAI MSA; later filing
   ≈ $11.9B OpenAI commitment through Oct 2030. Produces
   `RevenueAtRisk = Uncommitted + CancellableCommitted`,
   `Protected = NoncancellableTakeOrPay`. Render the ~$11.9B as a **disclosed contract
   envelope**, not a guaranteed minimum cash receipt (cancellation/tranche terms aren't
   public).

### Hero graph shape

A **solid structural triangle** (Microsoft / OpenAI / CoreWeave) surrounded by an **amber
behavioural network**. `CoreWeave → NVIDIA → TSMC → ASML` stays amber: dependency is
disclosed, but CoreWeave buys NVIDIA via just-in-time POs with no long-term capacity
guarantee → no fixed demand→revenue coefficient.

**Tagline:** *"We calculate what contracts and accounting rules force. We simulate what
management might choose."*

## Consequences

- The pitch may NOT promise a fully evidence-derived ripple from Microsoft to ASML.
- The solid edges do not chain under a *single* shock — they are three edges across
  different scenarios and two directions. Which single demo scenario lights enough solid
  edges to carry the animation is the next thing to grill.
- **Verification debt:** every figure above (27%, $3.1B, 35/62/77%, $15.1B, $11.55B,
  $11.9B) is demo-load-bearing and must be checked against the primary EDGAR filing before
  the demo — a mis-cited "solid" number is the exact sin this whole design hunts.
