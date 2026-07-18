# AI Fragility Map Demo MVP Design

## Summary

AI Fragility Map will be a data-first polished demo that shows how a decline in cloud/platform AI infrastructure spending could ripple through the AI supply chain. The first version focuses on a small network of real public companies, automated source ingestion from official documents, and an interactive network dashboard where the primary moment is a visible shock ripple moving from buyers to suppliers.

The MVP is a stress-test simulator, not a forecasting product. It should label all modeled outputs as scenario estimates and make the evidence basis visible wherever real company names and estimated flows appear.

## Goals

- Build a polished interactive dashboard centered on a ripple-through-map shock animation.
- Use real public company names in a focused 15-20 company universe.
- Start with the cloud/platform buyer shock scenario.
- Build a mostly automated data pipeline using SEC filings and official company annual reports or investor PDFs.
- Store extracted financial metrics, relationship evidence, confidence scores, and scenario outputs in a local database.
- Make data provenance visible enough that demo users can inspect why an edge or estimate exists.

## Non-Goals

- Do not build a broad market-wide AI bubble model in the first version.
- Do not include hundreds of companies.
- Do not treat modeled losses as predictions.
- Do not scrape informal web sources in the MVP.
- Do not require perfect extraction coverage before the dashboard can run.

## Initial Company Universe

The first universe should target these 20 real public companies:

- Cloud/platform buyers: Microsoft, Amazon, Alphabet, Meta, and Oracle.
- Chip and semiconductor suppliers: NVIDIA, AMD, Broadcom, Marvell, Micron, and SK hynix.
- Server, networking, and infrastructure suppliers: Supermicro, Dell, Arista, Vertiv, Schneider Electric, and Eaton.
- Semiconductor equipment suppliers: ASML, Applied Materials, Lam Research, and KLA.

If one of these companies lacks usable official-source documents during implementation, it may be replaced by a same-category public company. The implementation plan must document any replacement and the reason.

## Architecture

The system has four layers.

### Source Ingestion

The ingestion layer fetches and catalogs SEC filings and official company PDFs for the selected company universe. It records source metadata, including company, source type, filing or report date, URL or local path, retrieval status, and retrieval timestamp.

Source fetch failures should be recorded per document. A failed source must not prevent the rest of the pipeline or dashboard from running.

### Extraction Pipeline

The extraction pipeline parses filings and PDFs into text and tables, then extracts financial metrics and relationship evidence. It should look for:

- Revenue
- Cash and equivalents
- Debt
- Operating income
- Capital expenditure
- Interest expense
- Major customer disclosures
- Supplier and purchase commitment language
- Customer concentration percentages
- AI infrastructure, data-center, and semiconductor demand references

For financial metrics, the pipeline should prefer structured SEC facts where practical and fall back to parsed filing or PDF text when necessary.

For relationships, the pipeline should produce inspectable candidates rather than hidden assumptions. Candidate relationships should include extracted text, source references, parser method, confidence, and any derived numeric estimate.

### Scenario Model

The scenario model converts extracted or approved relationships into directed edges from buyer to seller. Each edge includes annual flow estimates, dependency weights, confidence scores, evidence references, and notes.

The first scenario is Cloud AI Spending Slowdown. The user selects a shock percentage such as 20%, 30%, or 40%, then runs the scenario. Direct supplier loss is calculated as:

```text
revenue_loss = annual_flow * shock_percent * pass_through_rate
```

Affected suppliers can reduce downstream spending in later rounds according to a simple propagation factor. The model runs for 2-3 rounds and stops when the maximum round is reached or incremental losses are too small to matter.

### Interactive Dashboard

The dashboard opens directly on the network map. It should not start with a marketing landing page.

The main interaction is a Run Shock action. When triggered, red loss pulses move outward from cloud/platform buyers to suppliers. The animation should make the direction and magnitude of losses understandable without reading a long explanation.

Supporting UI includes:

- Compact scenario controls for shock percent, pass-through rate, propagation rounds, and estimate mode.
- Results panel with total estimated revenue lost, affected companies, most fragile company, largest pathway, and stressed company count.
- Company panel with financial metrics, revenue at risk, stress status, major relationships, and evidence snippets.
- Edge inspection with annual flow estimate, dependency, confidence, and source basis.
- Replay or round scrubber for the ripple animation.

## Data Model

### `companies`

Stores company identity and financial metrics.

Fields include ticker, company name, sector group, fiscal period, revenue, cash, debt, operating income, capital expenditure, interest expense, and metric source references.

### `sources`

Stores ingested document metadata.

Fields include source ID, company ID, source type, filing or report date, URL, local path, extraction status, retrieval timestamp, and error message if applicable.

### `evidence_items`

Stores extracted evidence from official sources.

Fields include evidence ID, source ID, company ID, extracted text or table reference, evidence type, parser method, confidence, and source location metadata where available.

### `relationships`

Stores directed buyer-seller relationships.

Fields include relationship ID, buyer company ID, seller company ID, relationship type, annual flow low/base/high, dependency percentage, confidence score, evidence item IDs, estimation method, and notes.

### `scenario_runs`

Stores scenario configuration and outputs.

Fields include scenario ID, shock source group, shock percentage, pass-through rate, propagation factor, max rounds, estimate mode, run timestamp, per-company impacts, and per-edge pulse outputs.

## Confidence And Estimate Rules

Confidence describes evidence quality, not economic impact. It must not be multiplied into financial loss calculations.

Initial confidence rules:

- 1.00: exact disclosed amount from an official source.
- 0.90: disclosed customer concentration or revenue percentage.
- 0.60: disclosed relationship with value estimated from ranges or related metrics.
- 0.30: weak official-source evidence that implies a relationship but lacks a clear amount.

Estimate methods should be labeled as exact, percentage-derived, range-derived, or inferred. Low-confidence inferred edges can appear in the demo only when clearly marked.

## Stress Status

Companies can be labeled:

- Stable: low estimated impact.
- Exposed: meaningful revenue at risk but no severe stress signal.
- Stressed: revenue loss or operating income impact crosses configured thresholds.
- Critical: operating income turns negative, interest coverage becomes weak, or cash buffer appears insufficient under the scenario.

Initial thresholds:

- Exposed: revenue loss is at least 3% of annual revenue.
- Stressed: revenue loss is at least 8% of annual revenue, or operating income falls by at least 20%.
- Critical: operating income turns negative, interest coverage falls below 2.0, or estimated annual cash loss exceeds 25% of cash.

Thresholds should remain configurable, but these defaults define the first demo behavior. The MVP should prioritize explainability over complex financial modeling.

## Error Handling

- Source fetch failures are stored per source.
- Extraction failures produce `failed`, `partial`, or `needs_review` statuses.
- Missing metrics are shown as unknown and excluded from dependent calculations.
- Scenario runs continue when partial data exists, but the UI shows data quality warnings.
- Relationship edges with incomplete evidence must show low confidence or be excluded from the default view.
- The dashboard should handle empty or partial scenario results without crashing.

## Testing

The MVP should include focused tests for the credible parts of the system:

- Extractor tests using representative SEC and PDF text snippets.
- Model tests for direct loss, propagation rounds, stopping rules, and stress thresholds.
- Data validation tests for required fields, confidence score ranges, and buyer-seller consistency.
- UI tests for loading the dashboard, running a scenario, selecting a company, and replaying the ripple animation.

The test suite does not need to be exhaustive at first, but model math and data shape must be covered.

## User Experience Principles

- The first screen is the working map.
- The ripple animation is the hero interaction.
- Real company names are allowed, but every estimate is visibly labeled.
- The app should say estimated impact under scenario, not predicted loss.
- Evidence inspection should be close to the relevant edge or company.
- Controls should stay compact so the map remains visually dominant.

## Implementation Defaults

The implementation plan should start from these defaults:

- Pipeline: Python.
- Database: DuckDB.
- Dashboard: custom web app rather than Streamlit, so the network animation can be polished.
- Network rendering: a browser graph library with animated directed edges, selected during implementation.
- PDF parsing: a library that can extract both text and tables from official annual reports and investor PDFs.
- SEC source access: structured company facts where available, plus filing text for relationship evidence.
- Refresh command: a single local command that fetches sources, extracts candidates, updates DuckDB, and writes scenario-ready graph data.
