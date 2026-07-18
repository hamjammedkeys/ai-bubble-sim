# Final Fix Wave Report

## Status

Completed final-review fixes in one scoped change set. The previous Task 6 scratch
report has been removed from the product index and remains ignored locally.

## Delivered

- Added immutable `evidence_quote` and `source_location` fields to
  `StructuralRelationship`; the two numeric hero relationships now carry real SEC
  accessions, quotes, and source locations. The v2 edge payload emits the same fields.
- Rejected `/edit` requests that change a stored candidate's `source_id` or
  `source_accession`, and re-verification now uses the server-stored identity.
- Seeded a mechanically verified, unpromoted `proposed` CoreWeave/Microsoft
  concentration candidate for a fresh review store, including its primary-source quote
  and accession.
- Prevented the CoreWeave-to-NVIDIA diffuse edge from running unless the upstream
  CoreWeave take-or-pay exposure was activated.
- Added typed frontend edit submission that sends the complete review candidate to the
  server and refreshes only from the accepted API response.
- Made `targetCompanyId` nullable in the frontend contract. Unlinked candidates remain
  blue-striped review cards and are excluded from Cytoscape edges.

## Verification

- `pytest tests/test_hero_seed.py tests/test_api_v2.py tests/test_api_v2_payload.py -q`:
  19 passed.
- `make test`: 63 passed; one existing FastAPI/Starlette TestClient deprecation warning.
- `make lint`: passed.
- Frontend Vitest with Node 24.14.0: 5 passed.
- Frontend Vite build with Node 24.14.0: passed; existing bundle-size warning over 500 kB.
- Playwright Chromium: 1 passed.

## Environment Note

The application-bundled Node process cannot load the Rollup native module because macOS
rejects its team-signature pairing. The ignored frontend dependency tree was rebuilt from
`frontend/package-lock.json`; checks then ran with an official Node 24.14.0 binary in a
temporary directory. `npm ci` reported five dependency-audit vulnerabilities (three
moderate, one high, one critical); no dependency versions were changed as part of this fix.

## Source Company Identity Follow-up

- Rejected `/api/v2/review/{candidate_id}/edit` requests that alter the stored
  candidate's `source_company_id`, alongside the existing immutable source ID and
  accession checks.
- Added a parameterized API regression case that attempts the forged company ID and
  asserts a `422` response with the stored candidate left unchanged.
- Red/green evidence: the new case initially returned `200`; after the guard was
  added, `pytest -q tests/test_api_v2.py -k forged_source_identity` passed (3 cases).
- Final verification: `make test` passed (64 tests; one TestClient deprecation warning)
  and `make lint` passed.
