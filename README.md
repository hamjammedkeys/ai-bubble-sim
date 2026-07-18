# AI Fragility Map

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

## Test

```bash
make test
npm --prefix frontend run test -- --run
```

Install the root Playwright dependency, then run E2E with only the frontend dev server running. Playwright intercepts and mocks the API:

```bash
npm install
npm --prefix frontend run dev
npm run e2e
```

## Product Guardrails

- The first screen is the working map.
- The ripple animation is the hero interaction.
- Outputs are estimated impact under scenario, not predictions.
- Confidence is evidence quality and is not multiplied into economic impact.
