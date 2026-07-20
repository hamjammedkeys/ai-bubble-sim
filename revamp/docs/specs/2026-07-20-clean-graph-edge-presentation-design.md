# Clean graph edge presentation

## Goal

Remove the spaghetti effect introduced by collision-avoidance routing while keeping dense company relationships readable and inspectable in the Market Terminal graph.

## Presentation

- Render one restrained visual connection for each source/target company pair.
- When a pair contains multiple relationships, show a compact count badge such as `3 relationships` instead of drawing overlapping labels and curves.
- At rest, keep edge text minimal. Reveal the relationship summary on hover, keyboard focus, or selection.
- Keep curves shallow and deterministic. Do not fan every outgoing relationship into a separate large lane.
- The Evidence Desk remains authoritative for individual relationship type, filing passage, value, verification state, and review actions.

## Interaction

- Clicking or keyboard-activating a single-relationship connection opens that relationship directly.
- Activating a grouped connection selects a deterministic representative edge and exposes the group count; the Evidence Desk lets the user move between every relationship in that pair.
- Hover/focus continues to emphasize the two endpoint companies and dims unrelated graph elements.
- Scenario propagation and semantic colors remain edge-specific. If grouped edges have different active states, the grouped connection uses the highest-priority visible state: impact, exposure, unresolved, candidate, then inactive.

## Implementation boundaries

- Revert the fan-out/collision-routing behavior from `9444ba0`; preserve the fixed React Flow node dimensions from `fe8d6c6`.
- Build grouping and representative selection as pure functions in `app/lib/graph.ts` with regression tests.
- Do not change backend data or merge database relationships.
- Do not hide evidence: grouping affects only graph presentation.

## Acceptance criteria

- Dense CoreWeave–Microsoft–OpenAI data no longer produces large looping curves or stacked duplicate labels.
- Each company pair has one visible connection at rest.
- Multi-relationship pairs expose an accurate relationship count and all underlying evidence remains accessible.
- Mouse and keyboard inspection work without node-hover flicker.
- Scenario colors, layer filters, reduced motion, frontend tests, lint, and production build continue to pass.
