# AI Fragility Map

## Review-gated extraction

Live filing extraction produces typed, cited proposals that remain blue-striped and
`pending_human_review` after mechanical checks. Code verifies evidence tokens; a human
must approve, edit, or reject the candidate, and every decision is recorded in an audit log.

AI Fragility Map is a data-first polished demo that shows estimated ripple effects from a cloud/platform AI infrastructure spending slowdown.

## Backend

```bash
make install
make refresh
make api
```

## Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`.

## Verification

```bash
make test
make lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Install the root Playwright dependency, then run the browser regression. The Playwright
configuration starts the frontend dev server and mocks the API contract in the browser:

```bash
npm install
npx playwright test e2e/dashboard.spec.ts --project=chromium
```

## Compound credit event API contract

The dashboard only invokes `POST /api/v2/scenario/compound-credit-event`. Its fixed
hero request makes the observed shock state explicit:

```json
{
  "incremental_gaap_loss": 10000000000,
  "credit_status": "severe_distress",
  "default_status": "not_defaulted"
}
```

The response keeps evidence categories separate:

- `solid_red`: calculated, quantified **Impact**.
- `solid_orange`: activated contractual **Exposure**, not a realized loss.
- `dashed_amber`: realized loss is not identifiable because required credit inputs are missing.
- `diffuse_amber`: behavioural propagation is documented but its magnitude is not identifiable.

Review candidates are blue-striped until a human decision. Approvals and rejections are
returned by the review API and retained in the response audit log.

## Product Guardrails

- The first screen is the working map.
- The ripple animation is the hero interaction.
- Outputs distinguish calculated Impact, activated Exposure, and results that are not identifiable; none are predictions.
- Confidence is evidence quality and is not multiplied into economic impact.
