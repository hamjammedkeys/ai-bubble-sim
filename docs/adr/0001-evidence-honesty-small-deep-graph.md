# ADR 0001 — Small, deep graph with per-axis evidence provenance

Status: Accepted

## Context

The simulator's output is a chain of derived percentages (e.g. "OpenAI revenue −30% →
compute spend −18%"). Every such number is an **exposure multiplier** the analyst chose.
Under grilling, "these are all derived from filings" did not survive: filings give
revenue and capex totals, not sensitivity coefficients. Honest inventory of a broad
~15–20 entity / ~40 edge graph would be roughly *4 genuinely sourced marquee edges and
~35 vibes* — an evidence-backed pitch with a hole at its center, since the demo only looks
credible on the few edges prepared in advance.

Two separate weaknesses were identified:
1. **Coverage vs. defensibility.** A dense graph spreads effort so thin that most edges
   can't survive inspection.
2. **Label laundering.** A single confidence label per edge lets a *sourced company
   connection* imply that its *unsourced multiplier* is also evidence-backed.

## Decision

**Build a smaller, deeper graph, and score evidence per axis rather than per edge.**

Hackathon target:
- 8–12 entities, 12–18 meaningful edges.
- 4–6 directly quantified (Reported/Calculated) edges.
- 5–7 constrained-estimate edges.
- ≤ 3–5 assumption-driven edges.
- ⇒ roughly 60–75% defensible edges.

Multi-layer propagation (e.g. MSFT → OpenAI → CoreWeave/Azure → NVIDIA → TSMC → ASML) is
still demonstrable at this size; density is not the goal, surviving inspection is.

Each edge carries **four independent provenance scores** — *Relationship, Magnitude,
Propagation, Timing* — each labelled *Reported / Calculated / Constrained estimate /
Assumed / Hypothetical*. An edge may honestly read: Relationship=Reported,
Magnitude=Constrained estimate, Propagation=Assumed, Timing=Assumed.

## Consequences

- Supersedes the "15–20 company universe" sizing in the demo spec for the hackathon MVP.
- The UI must display the four axis-labels per edge; a single "confidence" badge is banned.
- Edge count is now a *quality* budget, not a coverage target — adding an edge means
  finding its sources, not filling the canvas.
- Open follow-ups (to grill next): how the four axes feed the fragility/Monte-Carlo layer,
  and which axis actually gates whether an edge is allowed to carry a shock at all.
