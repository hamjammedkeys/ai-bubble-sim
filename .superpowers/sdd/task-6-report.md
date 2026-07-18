# Task 6 Report — Legacy Frontend Retirement and Hero Regression

## Status

Completed and committed as `d6def99` (`test: lock compound credit event hero flow`).

## Delivered

- Replaced the legacy selectable cloud-slowdown control with one fixed compound-credit-event action and visible observed shock state.
- Removed the unused legacy `ScenarioControls` component. The typed frontend client already used only `/api/v2/scenario/compound-credit-event`; the browser regression also proves the legacy route is never requested.
- Added an audit-log rendering section so a rejected review candidate is visible after the API refresh.
- Added Chromium Playwright configuration and a browser regression covering v2 request JSON, Impact, Exposure, unidentifiable realized loss, pending review, and audit rejection.
- Updated README verification instructions, the exact v2 request body, and all four evidence-tier meanings.

## Verification

- `make test` — 57 passed (one existing FastAPI/Starlette deprecation warning)
- `make lint` — passed
- Frontend Vitest (run from `frontend` with bundled Node) — 3 passed
- Frontend Vite build (run from `frontend` with bundled Node) — passed; existing chunk-size warning over 500 kB
- Playwright Chromium regression (run with bundled Node) — 1 passed

## Concerns

- The environment did not expose `npm`/`npx`, so frontend checks used the bundled Node runtime and local executable entry points. The committed Playwright configuration uses the documented normal `npm --prefix frontend run dev` command for standard developer environments.

## Follow-up Review Fix

- Captured the compound-credit API request count immediately before clicking the hero action and asserted it increments by one after the click.
- Added an explicit assertion that the retired `Run shock` control has no rendered button.
- Verification was limited to `git diff --check`: this environment does not expose `node`, `npm`, `npx`, or a local executable Playwright/Vitest runtime, so the focused browser regression could not be run here.
