# ADR 0006 — LLM proposes, code verifies tokens, human gates semantics

Status: Accepted

## Context

Every honesty decision (ADRs 0001–0005) pushed the LLM out of the number-producing path:
filings supply numbers, invented multipliers are banned, the hero scenario is a preset. At
an AI hackathon this invites the fatal question: *"what does the LLM do that a person with
three highlighted PDFs and a D3 animation didn't?"* — under a pincer: if the LLM produces
the load-bearing numbers, they're either hand-verified (LLM added nothing trusted) or
unverified (the evidence-backed demo shows untrusted numbers — the core sin).

## Decision

**The LLM's load-bearing job is converting arbitrary financial prose into a *typed, cited,
reviewable candidate model* — never promoting its own proposal into evidence-backed state.**
Two distinct failure modes are defended by two distinct mechanisms:

- **Fabrication** → blocked by **code**, not the LLM.
- **Misinterpretation** → blocked by a **human reviewer**.

Pipeline: `document → relevant passages → entities → relationship type → affected financial
variable → proposed structural rule → limitations & missing parameters`. This is
cross-filing work a parser/D3 cannot do.

### Live second act

Start from the verified MSFT/OpenAI/CoreWeave triangle. The **judge picks an
unprocessed filing** (not revealed in advance) from several available.

1. **LLM reads it** → a review panel: proposed edge, typed, with the *supported calculation*
   and the *unsupported inference* explicitly separated. The filing opens at the exact
   passage with the entities/number/period highlighted.

2. **Mechanical checks run in code** (not the LLM): quoted text exists verbatim; the numeric
   token appears in the cited passage; entities named; period; unit; arithmetic valid;
   filing URL/accession resolves; no superseding amendment in the corpus. Screen shows each
   `✓`, and crucially: `Semantic interpretation — Pending human review`. These checks stop
   fabrication of evidence; they do **not** prove the interpretation is correct.

3. **Human makes a real decision** — Approve / Edit / Reject, which change **actual engine
   state**. A proposed edge is striped blue and cannot enter an evidence-backed simulation
   until approved; approval turns it solid and recalculates; rejection removes it.

### The signature integrity moment

The demo must **reject one plausible-but-invalid proposal** on stage — e.g. the LLM
applying CoreWeave's general "take-or-pay portfolio" language specifically to the OpenAI
contract. Rejection is logged in a visible **audit log** with the reason. This proves the
system is not an LLM-output visualizer.

## Consequences

- Requires: an extraction prompt producing typed candidates, a **code** verification layer
  (verbatim-quote match, token match, accession resolution — non-trivial against messy
  10-K HTML/XBRL), a review UI with real Approve/Edit/Reject wired to engine state, and an
  audit log.
- The "blue-striped candidate" is a new edge state on top of ADR 0005's four tiers.
- Trust boundary is explicit: the LLM is trusted to *find and type candidate structure*,
  never to assert final semantic truth or promote to evidence-backed.
