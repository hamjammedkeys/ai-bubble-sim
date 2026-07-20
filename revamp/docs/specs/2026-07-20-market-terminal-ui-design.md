# Market Terminal UI redesign

## Goal

Make FragilityGraph feel like a credible financial exposure terminal while remaining readable
to a general hackathon audience. The redesign must make the demo story legible on one screen:
choose a scenario, watch propagation, inspect its evidence, review a candidate, and read the
resulting risk summary.

## Scope

This work redesigns the existing frontend using the APIs and data already available. It covers
the global visual system, dashboard layout, graph presentation, evidence/review panel, scenario
controls, summary metrics, and state-change animation.

It does not add a 3D globe, new backend calculations, authentication, portfolio management,
background ingestion, or additional data providers. Missing values remain visibly unavailable;
the UI must never invent a financial metric to fill a card.

## Visual language

The selected direction is **Market Terminal**: square geometry, high information density, dark
surfaces, thin rules, compact labels, and strong numeric alignment.

### Typography

- Use IBM Plex Sans for navigation, labels, prose, citations, controls, and review content.
- Use IBM Plex Mono for monetary values, percentages, dates and periods, counters, statuses,
  node codes, and other scan-oriented data.
- Enable tabular numerals for financial figures so values align while changing.
- Body and evidence text must remain at least 13–14 px at the primary desktop breakpoint.
- Uppercase is limited to small labels and statuses; sentences and entity names retain normal
  casing for readability.

The fonts should be loaded through the existing Next.js font mechanism rather than an external
runtime stylesheet.

### Color and geometry

- Canvas: `#05090E`.
- Primary panel: `#0B1119`.
- Raised/selected surface: `#121922`.
- Hairline border: `#263140`.
- Primary text: approximately `#DCE3ED`; secondary text must maintain readable contrast.
- Exposure/warning: terminal yellow, approximately `#F5C542`.
- Accounting impact: red, approximately `#FF5263`.
- Candidate/unreviewed: blue, approximately `#4D9CFF`.
- Verification pass: green, approximately `#61D698`, used only for verified state.

Corners are square or at most 2 px. Shadows are avoided; separation comes from borders,
surface tone, and spacing. Buttons, inputs, nodes, cards, and panels follow the same geometry.

## Dashboard layout

The primary desktop screen is an **Exposure Desk** with four horizontal zones.

### 1. Terminal header

The compact top bar contains the product mark, workspace tabs, review-queue count, and a small
data-status indicator. Existing ingestion and review views remain accessible as tabs/panels;
the redesign does not create fake routes.

### 2. Market strip

A fixed-height metric strip shows the active scenario and the most decision-relevant values
available from current data:

- network entities;
- evidence-backed edges;
- total exposure at risk from the most recent run;
- accounting impact from the most recent run;
- unresolved hops.

Before a scenario has run, result-dependent cells show an em dash or explicit idle state rather
than zero.

### 3. Three-column workspace

- **Scenario Book (left):** lists existing scenarios, shows the active selection, exposes the
  existing create-scenario interaction, and provides the primary Run action. Layer toggles let
  users show or hide impact, exposure, unresolved, candidate, and inactive relationships.
- **Network Projection (center):** retains the graph as the hero surface. A subtle radar/grid
  projection replaces the large empty dotted canvas. It suggests a global system without the
  visual and implementation cost of a 3D globe. Nodes remain rectangular and show entity name
  plus type. Labels and edges must stay legible at the demo viewport.
- **Evidence Inspector (right):** shows the selected relationship, exact passage, filing link,
  structured value, mechanical checks, and Approve/Reject actions when the edge is a candidate.
  Selecting a company can reuse this area for company details, but evidence is the default after
  a scenario propagation or candidate selection.

### 4. Risk tape

A bottom strip summarizes the most recent scenario in plain financial language: shock summary,
impact, exposure at risk, identifiable hop count, and evidence coverage when that value can be
calculated from current graph data. Each number retains its evidence color and its semantic
label; exposure is never presented as realized loss.

## Interaction and animation

Animation communicates state changes rather than decorating the screen.

- Initial panels enter with short 120–180 ms staggered transitions.
- Running a scenario pulses the origin once, then traces propagation along each activated edge
  at roughly 700 ms per hop.
- Activated edges take their semantic color: red impact, yellow exposure, amber dashed
  unresolved. The inspector follows the currently activated edge.
- Result values count to their final values using tabular numerals.
- Candidate edges use a restrained blue marching dash. Approval stops that motion, briefly
  confirms verification, converts the edge to its evidence state, and decrements the queue.
- Hover or focus on an entity/edge emphasizes its local relationships and dims unrelated ones.
- No confetti, bouncing controls, or continuous ambient motion is allowed.
- `prefers-reduced-motion` disables path tracing, marching dashes, count-up, and staggered entry
  while preserving every final state.

## Responsive behavior

The hackathon demo targets a desktop projector/laptop viewport. At narrower widths, the right
inspector becomes an overlay/drawer and the scenario book becomes a compact selector above the
graph. The risk tape may scroll horizontally rather than compress financial labels below their
readable size. Mobile-specific graph interaction is not part of this pass.

## Data and state

The redesign consumes the current entity, edge, candidate, scenario, scenario-run, and edge
detail endpoints. Derived dashboard metrics must be computed from those responses in a small,
pure frontend data layer rather than embedded throughout JSX.

The page keeps a single selected scenario, selected entity/edge, active graph filters, current
view, and most recent run result. Existing API errors remain visible within the relevant panel;
a failed action must not clear the last successful graph or scenario result.

## Implementation boundaries

- Preserve the current API client contract unless a missing value makes a specific design
  element impossible.
- Extract reusable terminal primitives and dashboard sections from the current monolithic page
  only where the redesign needs them; do not perform an unrelated application rewrite.
- Keep graph calculations and visual-state mapping in the existing graph utility layer.
- Global design tokens, focus styles, reduced-motion rules, and base typography live in the
  global stylesheet.
- Accessibility includes keyboard-operable controls, visible focus, semantic buttons, readable
  contrast, and non-color labels for relationship meaning.

## Acceptance criteria

- The desktop screen visibly matches the approved Market Terminal direction: square panels,
  dark terminal palette, IBM Plex Sans/Mono roles, aligned numbers, and compact hierarchy.
- The main viewport simultaneously exposes scenario selection, graph, evidence, and risk summary.
- Every existing frontend workflow remains usable: ingest/extract, inspect, approve/reject,
  create/run scenarios, and inspect company details.
- Scenario animation communicates origin, propagation order, edge type, and final result without
  changing calculated values.
- Candidate approval produces a clear visual state transition without implying that LLM output
  was already verified.
- Idle, loading, error, empty, and reduced-motion states are designed and tested.
- Existing frontend lint/build checks pass, and tests cover pure dashboard derivations plus the
  primary interaction state transitions at an appropriate seam.
