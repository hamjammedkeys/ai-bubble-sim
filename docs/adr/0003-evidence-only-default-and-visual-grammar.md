# ADR 0003 — Evidence-only default; the ripple's dissolve is the hero visual

Status: Accepted (resolves the open tension in ADR 0002)

## Context

The hero animation is a shock rippling across the network. But evidence-only mode
(ADR 0002) stops a quantified shock at the first unconstrained propagation edge, and
elasticity (`β`) is the thinnest-sourced axis — so a fully quantified six-hop ripple would
require user-assumed numbers, i.e. exactly the false precision ADR 0002 forbids.

## Decision

**Default state is evidence-only mode.** The animation still travels all the way to ASML,
but past the first unsupported `β` it stops representing *quantified financial impact* and
starts representing *possible exposure through a documented dependency* — and that switch
is rendered *in the animation itself*, never buried in a tooltip.

Visual grammar:

| Appearance | Meaning |
|---|---|
| Solid red pulse | Quantified propagation |
| Red node with range | Supported numerical impact (e.g. OpenAI −4% to −7%) |
| Amber break marker | Evidence becomes insufficient (the dissolve point) |
| Hollow dashed pulse | Documented path, unknown magnitude |
| Amber outlined node | Exposed, but impact not identifiable |
| Diffuse pulse (wider, more transparent) | Increasing epistemic uncertainty (not a bigger/smaller shock) |
| Grey edge | Relationship not reached |

Rules that fall out:
- **No vulnerability ranking for unquantified nodes.** NVIDIA cannot be "#3 most
  vulnerable" when no supported number exists.
- The result panel splits *Quantified impact* from *Downstream exposure detected* from
  *Numerical impact cannot be identified (missing parameter: …)*.
- Scenario mode is a **secondary, opt-in** action ("Explore with explicit assumptions").
  Nothing is assumed automatically.

**Product promise changes** from the indefensible "Watch the calculated shock ripple
through the AI economy" to **"See how far a shock can reach — and where the evidence stops
supporting a numerical answer."** The dissolve from solid to diffuse *is* the signature
visual.

## Consequences

- Front-end must encode the solid→amber→diffuse states and a break marker, not just node
  coloring.
- **Load-bearing assumption — now CONFIRMED BROKEN for behavioral β (grilling, Q5).** No
  filing/transcript constrains a *behavioral* propagation elasticity (revenue→spending,
  capex→orders) anywhere in the MSFT→OpenAI→CoreWeave→NVIDIA→TSMC→ASML chain. Disclosures
  cover relationship existence, ownership %, concentration, purchase obligations, segments
  — never "how much the next company's behaviour changes." So a solid-red *behavioral* hop
  does not exist. The one apparent exception (Microsoft equity-method accounting for
  OpenAI, ~27% ownership) is an **accounting pass-through** (OpenAI result → MSFT reported
  income), the wrong direction and not a behavioural β. Open question moved to a fresh
  grill: does the solid-red phase relocate from *behavioral* to *structural/contractual*
  propagation? (To be resolved in a follow-on ADR.)
