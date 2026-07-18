# ADR 0005 — Hero scenario: a compound credit event; impact ≠ exposure

Status: Accepted (extends the grammar of ADR 0003, resolves the demo-scenario question in ADR 0004)

## Context

ADR 0004 left three solid edges that don't chain under one shock. A single-solid-hop demo
is honest but undersells. A two-edge "OpenAI distress" demo survives scrutiny **only if**
the two edges are rendered as *different mathematical objects*: one is a calculated
accounting **impact**, the other is an activated credit **exposure** — not two losses.

The tempting error is "OpenAI distress → CoreWeave loses $11.9B." That is not deterministic:
realized loss needs credit parameters `ExpectedLoss = EAD × PD × LGD` (exposure at default,
probability of default, loss given default) plus timing — none disclosed. Missing values
here are **credit parameters, not behavioural elasticity**; the edge is β-free but still not
a solid *loss*.

## Decision

### The hero scenario is a precisely specified compound credit event

Not the vague "large loss." One preset carrying explicit observed states:

```
OpenAI reports a $10B incremental GAAP net loss AND enters severe credit distress.
  Incremental GAAP net loss: $10B
  Credit status: severe distress
  Default status: not yet defaulted
```

One button → two **parallel, structurally distinct** consequences:

- **OpenAI → Microsoft (equity method):** calculated accounting impact
  `≈ 27% × −$10B = −$2.7B` (indicative; subject to basis adjustments, ownership timing,
  loss-recognition limits). A quantified **impact**.
- **OpenAI → CoreWeave (take-or-pay):** the ~$11.9B contract envelope is *activated as
  exposure*. CoreWeave's S-1/A discloses the envelope, significant counterparty credit
  exposure, and mitigations (prepayments, letters of credit, guarantees) that "cannot
  eliminate" credit risk. A quantified **exposure**, not a realized loss.

### Impact ≠ Exposure (the load-bearing distinction)

- **Impact** — a loss the disclosed rule *forces* (equity-method share of a stated loss).
- **Exposure** — an amount *placed at risk* by the event, whose realized loss depends on
  undisclosed parameters. Rendering exposure as impact is the central dishonesty this
  product exists to refuse.

### Rendering tiers (extends ADR 0003's grammar)

| Rendering | Meaning |
|---|---|
| Solid red | Calculated accounting **impact** (MSFT ≈ −$2.7B) |
| Solid orange | Quantified **exposure at risk** (CoreWeave up to ~$11.9B activated) |
| Dashed amber | Assumption-dependent realized loss (needs EAD·PD·LGD) |
| Diffuse amber | Behavioural downstream response (CoreWeave capex → NVIDIA → …) |

Headline:
```
Microsoft:            ≈ $2.7B indicative accounting impact
CoreWeave:            up to $11.9B contract exposure activated
CoreWeave expected loss:  not identifiable (credit parameters undisclosed)
```

## Consequences

- The front-end needs a **four-tier** edge/node state, not two (solid/amber).
- The shock input model must carry *multiple explicit observed states* (loss amount +
  credit status + default status), not a single slider value — a vague scalar "distress"
  cannot fire the equity edge.
- Reinforces ADR 0004's verification debt: $2.7B is illustrative (27% × $10B); the *actual*
  disclosed FY26 Q1 figure was $3.1B — the demo must not blur an illustrative calc with a
  reported number.
