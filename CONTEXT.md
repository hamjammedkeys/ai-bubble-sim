# AI Fragility Map — Context

The living spec for **AI Fragility Map**: a data-first demo that shows how a shock to
AI-infrastructure spending ripples through a network of real public companies, with the
evidence basis for every edge made inspectable.

This file and `docs/adr/` are maintained by grilling sessions (`/grill-with-docs`). They
capture decisions and shared vocabulary as they get *resolved* — not upfront. The full
product spec lives at
[`docs/superpowers/specs/2026-07-18-ai-fragility-map-demo-design.md`](docs/superpowers/specs/2026-07-18-ai-fragility-map-demo-design.md).

## Glossary

Terms are added here as grilling resolves their meaning. Each term is defined once and
referenced everywhere.

- **Edge** — a directed relationship between two entities that a shock can propagate
  along (e.g. `OpenAI → Azure`, compute spending).

- **Exposure multiplier** — the coefficient on an edge that converts a shock to the
  source into an impact on the target (e.g. a 30% revenue drop × `0.6` → 18% compute-spend
  drop). Its credibility is the credibility of the whole simulator; see
  [ADR 0001](docs/adr/0001-evidence-honesty-small-deep-graph.md).

- **Evidence provenance** — how an edge is justified, scored **separately on four axes**
  so a sourced connection can't launder an unsourced multiplier into an "evidence-backed"
  result:
  - *Relationship* — do we know the connection exists?
  - *Magnitude* — do we know how large the flow is?
  - *Propagation* — do we know how a shock to one side changes the other?
  - *Timing* — do we know when the effect appears?

- **Provenance label** — the standard met on a given axis, in descending strength:
  - *Reported* — the number appears directly in a source.
  - *Calculated* — a mathematical transformation of reported numbers only.
  - *Constrained estimate* — a source establishes bounds; assumptions select the value/range.
  - *Assumed* — the relationship is sourced, but the sensitivity is analyst-defined.
  - *Hypothetical* — the relationship itself exists only for scenario exploration.

  (Replaces the earlier single three-way `fact / inference / unknown` idea, which let one
  label stand for an entire edge.)

- **Elasticity (β)** — on an edge, how strongly the target variable responds to a shock in
  the source (e.g. how much OpenAI's compute spend responds to its revenue). Distinct from
  **Exposure**, the size of the flow. Both multiply the shock; either can be unconstrained.

- **Structural propagation** — a shock traveling by *disclosed financial structure*
  (equity method, take-or-pay/purchase obligations, customer concentration, ownership,
  debt schedules). Deterministic and sourced → the *solid-red* quantified layer. Each
  structure produces its own object (accounting impact, exposure bound, revenue floor…) —
  they must not all be called "predicted revenue impact". See
  [ADR 0004](docs/adr/0004-structural-core-amber-periphery.md).

- **Behavioural propagation** — a shock traveling by management *choice* (revenue→capex,
  capex→orders). Never disclosed as an elasticity → always the *amber* dissolve unless
  empirically estimated.

- **Impact vs Exposure** — the distinction the product lives on; see
  [ADR 0005](docs/adr/0005-hero-scenario-impact-vs-exposure.md). *Impact* is a loss a
  disclosed rule *forces* (e.g. equity-method share of a stated net loss) → solid red.
  *Exposure* is an amount *placed at risk* whose realized loss needs undisclosed parameters
  (`ExpectedLoss = EAD × PD × LGD` + timing) → solid **orange**, never printed as a loss.
  Rendering exposure as impact is the central dishonesty this product refuses.

- **Edge-flow vs aggregate shock (the guardrail)** — a shock applied directly to a
  *disclosed edge flow* ("MSFT purchases from CoreWeave −20%") propagates solid; a shock to
  an upstream *financial aggregate* ("MSFT earnings −20%") that only reaches the edge via
  behaviour is amber. Dressing the second as the first secretly reintroduces behavioural β.

- **Propagation mode** — how the engine treats an unconstrained multiplier; see
  [ADR 0002](docs/adr/0002-three-propagation-modes-no-default-point-value.md):
  - *Evidence-only* — the shock stops at the unconstrained edge ("not identifiable from
    evidence"; not the same as zero).
  - *Scenario* — the user supplies the missing range; output is an interval, presented as
    conditional on that choice, never as a point.
  - *Sensitivity* — output shown as a function of the unknown, plus the decision threshold
    at which the conclusion flips.

- **Candidate edge** — an LLM-proposed, typed, cited graph update. Rendered blue-striped;
  cannot enter an evidence-backed simulation until a human Approves. See
  [ADR 0006](docs/adr/0006-llm-proposes-code-verifies-human-gates.md).

- **Mechanical check vs semantic review** — the two-mechanism trust boundary. *Mechanical
  checks* are run in **code** (verbatim quote exists, numeric token present, entities/period/
  unit match, arithmetic valid, accession resolves) and block *fabrication*. *Semantic
  review* is a **human** Approve/Edit/Reject that blocks *misinterpretation*. The LLM is
  trusted to find and type candidate structure, never to assert final truth.

## Open / deferred

- **Build order & cut-line — deferred by choice.** Grilled but not resolved: which half
  (static verified triangle + animation, vs. live extraction + rejection moment) is the
  demo if only one gets finished, and what drops first when behind. Owner decided not to
  settle this now.
- **Verification debt — outstanding, load-bearing.** Every filing figure the "solid" tiers
  depend on (27% ownership, $3.1B FY26Q1 income effect, ~$11.9B OpenAI commitment, 35/62/77%
  concentration, $15.1B RPO) must be checked against primary EDGAR sources before any demo.
  A mis-cited "solid" number is the exact failure this whole design exists to avoid.

## Decisions

See `docs/adr/` for the full log. Most recent first:

- [0006](docs/adr/0006-llm-proposes-code-verifies-human-gates.md) — The LLM proposes typed,
  cited *candidate* edges; **code** verifies the tokens (blocks fabrication); a **human**
  Approves/Edits/Rejects (blocks misinterpretation). Signature moment: rejecting a
  plausible-but-invalid proposal on stage, logged in an audit trail.
- [0005](docs/adr/0005-hero-scenario-impact-vs-exposure.md) — Hero scenario is a compound
  credit event ("OpenAI: +$10B GAAP loss, severe distress"). One button fires two
  structurally distinct results: MSFT calculated accounting *impact* (solid red) and
  CoreWeave activated *exposure* (solid orange). Four rendering tiers, not two.
- [0004](docs/adr/0004-structural-core-amber-periphery.md) — The quantified layer is
  *structural* propagation (equity method, take-or-pay, concentration), not behavioural.
  Hero graph = a solid MSFT/OpenAI/CoreWeave triangle in an amber behavioural network.
  Promise: "We calculate what contracts and accounting rules force. We simulate what
  management might choose."
- [0003](docs/adr/0003-evidence-only-default-and-visual-grammar.md) — Evidence-only is the
  default; the ripple travels to ASML but visibly dissolves from solid (quantified) to
  diffuse (documented-but-unquantified) at the first unsupported β. That dissolve is the
  hero visual. Promise: "See how far a shock can reach — and where the evidence stops."
- [0002](docs/adr/0002-three-propagation-modes-no-default-point-value.md) — An assumed
  multiplier gets no default point value; the engine runs in evidence-only, scenario, or
  sensitivity mode instead of fabricating a number.
- [0001](docs/adr/0001-evidence-honesty-small-deep-graph.md) — A small, deep graph
  (8–12 entities, 12–18 edges) with per-axis multi-label evidence provenance, chosen over
  broad coverage, because defensibility per edge is the product's whole claim.
