# Safe content and chat scenario card

## Goal

Prevent long URLs or unbroken text from widening the Evidence Desk and Copilot, give all scrollable terminal surfaces a consistent scrollbar, and turn successful chat-created scenarios into actionable in-chat UI.

## Content containment

- Evidence passages, document links, chat messages, tool errors, scenario names, and other user/external text must shrink within their panel.
- A shared `content-safe` utility applies `min-width: 0`, `max-width: 100%`, `overflow-wrap: anywhere`, and `word-break: break-word`.
- Evidence Desk and Copilot message areas scroll vertically and do not create page-level horizontal scroll.
- Risk Tape keeps its intentional horizontal scrolling behavior.
- URL safety remains unchanged: only validated HTTP(S) links become anchors.

## Scrollbars

- Scrollable Market Terminal surfaces use a shared `terminal-scrollbar` class.
- Chromium/WebKit scrollbar width is 8px; the track uses the canvas/surface color, the thumb uses the hairline color, and hover increases contrast without adding a bright accent.
- Firefox uses `scrollbar-width: thin` and matching `scrollbar-color`.
- Scrollbars must not reduce content width enough to reintroduce overflow at narrow viewports.

## Chat message model

The API contract remains `ChatReply { reply, actions }`, but the Copilot stores a frontend message view-model that retains the assistant response's actions. User messages have no actions.

Action parsing is pure and defensive. It recognizes successful `create_scenario` and `run_scenario` actions, ignores malformed/error results, and associates a run with the scenario name used by the tool call. Unknown tools remain invisible in the card UI but continue to be available in the raw API response during the send operation.

## Scenario action card

A successful `create_scenario` renders one square inline card beneath the corresponding assistant reply with:

- scenario name;
- origin company;
- magnitude and unit;
- terminal status;
- one primary action.

### Created but not run

- Status: `READY`.
- Primary action: `Run scenario`.
- The action calls the same parent scenario-propagation flow used by the Scenario Book, selects the new scenario, animates the graph, and refreshes the dashboard.

### Created and run in the same response

- Status: `RUN COMPLETE`.
- Show real impact, exposure, and unresolved totals from the successful `run_scenario` tool result.
- Primary action: `View on graph`, which selects the scenario and closes or de-emphasizes the Copilot without running it again.

### Failure states

- Tool results containing `error` do not produce a success card.
- A card-level Run failure appears with `role="alert"`; it does not remove scenario details or the prior successful graph state.
- The Run button is disabled only while that card is running.

## Parent integration

- Refactor the current scenario runner into an ID-driven callback so Scenario Book and Copilot share one propagation implementation.
- Avoid `setSelectedScenarioId` followed immediately by a stale closure call; the run callback receives the scenario ID explicitly.
- The existing chat text, graph refresh behavior, drawer focus, reduced-motion behavior, and evidence review flows remain unchanged.

## Responsive behavior

- Copilot width remains desktop-oriented but clamps to the viewport on narrow screens.
- The chat message scroller and input row use `min-width: 0`; input and Send button remain visible without horizontal page scroll.
- Scenario cards use the terminal square geometry and stack their metrics when width is constrained.

## Testing and acceptance criteria

- Long SEC URLs wrap inside Evidence Desk and Copilot at the narrow target viewport without document-level horizontal overflow.
- Evidence Desk, Copilot, Scenario Book, and other vertical terminal scrollers share the approved scrollbar appearance; Risk Tape still scrolls horizontally.
- Pure tests cover action parsing for create-only, create-plus-run, malformed, and error results.
- Component tests cover READY and RUN COMPLETE card copy, totals, buttons, busy state, and card-level error semantics.
- Browser verification covers a long URL, Run from chat using the normal propagation sequence, View on graph for an already-run scenario, and narrow viewport containment.
- Frontend tests, lint, TypeScript, production build, and `git diff --check` pass.
