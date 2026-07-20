# Headline-figures verification: Microsoft↔OpenAI, OpenAI↔CoreWeave, Amazon↔Anthropic

**Purpose.** CONTEXT.md and ADR 0004 flag a set of demo-load-bearing figures as "verification
debt — outstanding": *27% ownership, $3.1B FY26Q1 income effect, ~$11.9B OpenAI commitment,
35/62/77% concentration, $15.1B RPO*. This note follows each of those figures back to the SEC
filing that owns it — not a news write-up of the filing — quotes the exact sentence, and gives
a plain match/diverges verdict. All filings were fetched directly from sec.gov/Archives with a
descriptive User-Agent (SEC EDGAR requires one; generic fetch tools get HTTP 403). Amounts are
as originally stated in each filing (no unit conversion).

---

## 1. Microsoft ↔ OpenAI

### 1.1 Accounting method and total funding commitment

**Filing:** Microsoft Corp, Form 10-K, fiscal year ended June 30, 2025, filed 2025-07-30.
CIK 0000789019, accession 0000950170-25-100235.
URL: https://www.sec.gov/Archives/edgar/data/789019/000095017025100235/msft-20250630.htm

> "Therefore, our VIE investments are not consolidated and the majority are accounted for
> under the equity method of accounting. We have an investment in OpenAI Global, LLC
> ("OpenAI") and have made total funding commitments of $13 billion. The investment is
> accounted for under the equity method of accounting."

**Verdict:** Demo currently uses: "$13B funding commitments, equity-method accounting" →
Filing says: exactly that → **MATCH**. Note this FY2025 10-K (filed before OpenAI's October
2025 recapitalization) does **not** disclose any ownership percentage for OpenAI — no "27%,"
no "49%," nothing. A percentage first appears in a later filing (below).

### 1.2 Ownership percentage ("~27% as-converted")

**Filing A (first disclosure, as a subsequent event):** Microsoft Corp, Form 10-Q, quarter
ended September 30, 2025 (FY2026 Q1), filed 2025-10-29. Accession 0001193125-25-256321.
URL: https://www.sec.gov/Archives/edgar/data/789019/000119312525256321/msft-20250930.htm

> "NOTE 17 — SUBSEQUENT EVENT. On October 28, 2025, we signed a new definitive agreement
> with OpenAI... Additionally, OpenAI has formed a public benefit corporation ("PBC") and
> completed a recapitalization. As a result of the recapitalization, Microsoft holds
> approximately 27 percent in the PBC on an as-converted diluted basis... We will continue
> to account for our $13 billion of total funding commitments to OpenAI as an investment
> under the equity method of accounting."

**Filing B (most recent 10-Q, stated as a current fact, not a subsequent event):** Microsoft
Corp, Form 10-Q, quarter ended March 31, 2026 (FY2026 Q3), filed 2026-04-29. Accession
0001193125-26-191507.
URL: https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm

> "We have an investment of approximately 27 percent of OpenAI on an as-converted basis
> accounted for under the equity method of accounting... As a result of the OpenAI
> Recapitalization, we had a decrease in our proportionate ownership of OpenAI and recorded
> a dilution gain in other income (expense), net."
>
> "We have made total funding commitments of $13 billion, of which $11.8 billion has been
> funded as of March 31, 2026."
>
> "...using the hypothetical liquidation at book value ("HLBV") method because our
> liquidation rights and priorities differ from our underlying ownership interest."

**Verdict:** Demo currently uses: "27% equity method" → Filing says: "approximately 27
percent... on an as-converted diluted basis," equity method, confirmed both as of the Q1
FY26 subsequent-events note and restated as a standing fact in the most recent 10-Q →
**MATCH**, with one caveat the demo should carry: the 27% is **not** a stable historical
constant — it dates specifically to the October 28, 2025 recapitalization and is disclosed
under the HLBV variant of equity-method accounting (liquidation rights differ from ownership
%), not a plain pro-rata equity method. Pre-recap filings (FY2025 10-K) disclosed no
percentage at all, so "27%" should not be presented as "Microsoft's OpenAI stake" timelessly
— it is accurate for the current/most recent filing only.

### 1.3 Income-statement effect ("$3.1B FY26Q1")

Same 10-Q as Filing A above (quarter ended September 30, 2025 — Microsoft's fiscal Q1 2026).
Two different, easily-confused dollar figures both appear in this filing, in different notes:

> **MD&A, Results of Operations (net-income-line effect — the number the demo cites):**
> "Current year net income and diluted EPS were negatively impacted by net losses from
> investments in OpenAI, which resulted in a decrease in net income and diluted EPS of
> $3.1 billion and $0.41, respectively. Prior year net income and diluted EPS were
> negatively impacted by net losses from investments in OpenAI, which resulted in a decrease
> in net income and diluted EPS of $523 million and $0.07, respectively."

> **Note 3 — Other Income (Expense), Net (a different, larger, pre-allocation figure):**
> "For the three months ended September 30, 2025 and 2024, other income (expense), net
> included $4.1 billion and $688 million, respectively, of net losses from investments in
> OpenAI, primarily net recognized losses on our equity method investment."

**Verdict:** Demo currently uses: "$3.1B FY26Q1 income effect" → Filing says: "$3.1 billion"
decrease in net income for the quarter ended September 30, 2025 → **MATCH**, verbatim and
correctly attributed to the right quarter. **Important nuance the demo must not blur** (this
is exactly the distinction ADR 0005 already anticipates between the $2.7B illustrative calc
and the real $3.1B): the filing separately reports a **$4.1 billion** figure for the *same
quarter* in the Other Income (Expense) note — that is the pre-tax/pre-allocation net loss
recognized in that P&L line item, while $3.1B is the resulting *net income* decrease. Do not
substitute one for the other; cite $3.1B specifically as "the net-income effect" if that is
the number being surfaced.

**Further honesty caveat, found while checking the most recent 10-Q:** the $3.1B loss is one
volatile quarter in a series that swings sign. Same company, later quarters (from Filing B,
quarter ended March 31, 2026):

> "Current year net income and diluted EPS were **positively** impacted by net gains from
> investments in OpenAI, which resulted in an increase in net income and diluted EPS of
> $4.5 billion and $0.60, respectively." (Q3 FY2026, three months ended March 31, 2026)
>
> "Current year net income and diluted EPS were negatively impacted by net losses from
> investments in OpenAI, which resulted in a decrease in net income of $14 million." (nine
> months ended March 31, 2026, cumulative)

So the FY2026 nine-month cumulative OpenAI effect on Microsoft's net income is close to
*flat* ($14 million), because a $4.5B Q3 gain largely offset the $3.1B Q1 loss (plus a
smaller Q2 loss). **If the demo presents "$3.1B" as if it were a steady-state or annualized
number, that would misrepresent the filings — it is real, correctly quoted, and belongs to
one specific quarter, but the same line item was a $4.5B gain two quarters later.** Frame it
explicitly as "Q1 FY2026 quarterly result," not as Microsoft's general OpenAI exposure.

---

## 2. OpenAI ↔ CoreWeave

### 2.1 Purchase commitment (~$11.9B through Oct 2030)

**Filing:** CoreWeave, Inc., Form S-1/A (second/final pre-IPO amendment), filed 2025-03-20.
CIK 0001769628, accession 0001193125-25-058309.
URL: https://www.sec.gov/Archives/edgar/data/1769628/000119312525058309/d899798ds1a.htm

> "Following December 31, 2024, we entered into a master services agreement with OpenAI...
> that, as of March 2025, provided for payments to us of up to approximately $11.9 billion
> through October 2030, subject to satisfaction of delivery and availability of service
> requirements."
>
> "...in March 2025, we entered into a master services agreement with OpenAI, a private
> company, pursuant to which OpenAI has committed to pay us up to approximately $11.9
> billion through October 2030."

Confirmed still current in CoreWeave's **most recent 10-Q** (quarter ended March 31, 2026,
filed 2026-05-08, accession 0001769628-26-000222):

> "...in March 2025, we entered into a master services agreement with OpenAI, a private
> company, pursuant to which OpenAI has committed to pay us up to approximately $11.9
> billion through October 2030. Other significant customers include Microsoft and Meta."

**Verdict:** Demo currently uses: "~$11.9B OpenAI commitment through 2030" → Filing says:
exactly that, and it is unchanged from the original S-1/A through the most recent 10-Q
thirteen months later → **MATCH**.

**Two things to flag so the demo doesn't overstate or misattribute this figure:**

1. **A second, unrelated $11.9 billion appears in the same S-1/A** — CoreWeave's data-center
   lease commitments: "In August 2025, the Company entered into additional lease
   agreements... The aggregate amount of estimated future undiscounted lease payments
   associated with such leases is $11.9 billion." This is a coincidental dollar match with a
   completely different obligation (real-estate leases, not the OpenAI contract). Anyone
   grepping the filing for "$11.9 billion" could accidentally cite the wrong one — the demo's
   extraction/verification pipeline should disambiguate by requiring "OpenAI" and "October
   2030" co-occur with the figure, not just the number.
2. **The $11.9B is not OpenAI's only disclosed commitment to CoreWeave.** The most recent
   10-Q additionally discloses: "In May 2025, we entered into a master services agreement
   with OpenAI OpCo, LLC ('OpenAI') and in September 2025, we entered into an order form
   under this master services agreement pursuant to which OpenAI has committed to pay us up
   to approximately $6.5 billion through May 31, 2031." If the demo wants a single
   "OpenAI→CoreWeave total contracted" figure as of the most recent filing, the accurate
   figure is **two separate commitments ($11.9B through Oct 2030 + $6.5B through May 2031)**,
   not a single $11.9B ceiling. Presenting $11.9B alone is not wrong (it is the original,
   still-valid MSA figure), but it understates CoreWeave's current total disclosed OpenAI
   exposure if read as of the latest filing.

### 2.2 The $11.55B figure (distinguishing it from $11.9B)

Same S-1/A as above:

> "Microsoft, our largest customer for the years ended December 31, 2023 and 2024, will
> represent less than 50% of our expected future committed contract revenues when combining
> our RPO balance of $15.1 billion as of December 31, 2024 and up to $11.55 billion of future
> revenue from our recently signed Master Services Agreement with OpenAI, as described
> herein."

**Verdict:** This is a **real, separately-disclosed figure in the same filing as $11.9B**,
used specifically in the "customer concentration won't exceed 50%" argument. The filing does
not spell out the arithmetic, but $11.9B − $0.35B (see below) = $11.55B, which is consistent
with OpenAI's committed cash-pay amount net of the $350 million of CoreWeave stock OpenAI
received as part of the deal (also disclosed in the same filing: "OpenAI became an investor
in CoreWeave through the issuance of $350.0 million of CoreWeave stock as part of the initial
agreement"). **Not found: an explicit sentence in the filing stating this reconciliation** —
the $11.55B/$11.9B relationship is inferred by us from the numbers, not asserted by CoreWeave.
The demo should treat $11.9B as the headline commitment and, if it uses $11.55B at all, label
it precisely as "future revenue net of the equity component," not as a second independent
commitment.

### 2.3 Remaining Performance Obligations ($15.1B)

**Filing:** CoreWeave, Inc., Form S-1 (original), filed 2025-03-03. Accession
0001193125-25-044231.
URL: https://www.sec.gov/Archives/edgar/data/1769628/000119312525044231/d899798ds1.htm

> "As of December 31, 2024, we had $15.1 billion of remaining performance obligations
> reflecting an increase of 53%, from $9.9 billion as of December 31, 2023."
>
> "As of December 31, 2024, the Company had $15.1 billion of unsatisfied RPO, of which 54%
> is expected to be recognized over the initial 24 months ending December 31, 2026, 42%
> between months 25 and 48, and the remaining balance recognized between months 49 and 72."

**Verdict:** Demo currently uses: "$15.1B RPO (end-2024)" → Filing says: exactly that,
present in the *original* S-1 (i.e., before the OpenAI deal was even signed — this RPO figure
is Microsoft/other-customer driven, not OpenAI-driven) → **MATCH**. Note RPO has since grown
substantially — CoreWeave's Q2 2025 10-Q (filed 2025-08-13, accession 0001769628-25-000041)
shows total unsatisfied RPO of $30.1 billion as of June 30, 2025 — so if the demo ever
updates to a "current" RPO figure rather than the historical end-2024 figure, $15.1B should
not be presented as still-current.

### 2.4 Customer concentration (35% / 62% / 77%)

Same original S-1 as 2.3 above.

> "For the year ended December 31, 2022, our largest customer accounted for 16% of our
> revenue. For the years ended December 31, 2023 and 2024, our largest customer was
> Microsoft, which accounted for 35% and 62% of our revenue, respectively."
>
> "We recognized an aggregate of approximately 77% of our revenue from our top two customers
> for the year ended December 31, 2024. None of our other customers represented 10% or more
> of our revenue for the year ended December 31, 2024."

**Verdict:** Demo currently uses: "MSFT = 35% (2023), 62% (2024) of revenue; top-2 = 77%
(2024)" → Filing says: exactly that, verbatim, annual figures → **MATCH**.

**Caveat for anyone extending this edge with more recent data:** these are *annual* figures.
CoreWeave's quarterly 10-Qs disclose different, quarter-specific percentages for "Customer A"
(confirmed elsewhere in the same 10-Qs to be Microsoft) that should not be mixed with the
annual 35/62/77% without saying so:
- Q2 2025 10-Q (filed 2025-08-13): "approximately 71% and 59% of our revenue for the three
  months ended June 30, 2025 and 2024, from our largest customer, Microsoft."
- Most recent 10-Q, Q1 2026 (filed 2026-05-08): "Customer A 45%, Customer B 20%" for the
  three months ended March 31, 2026, versus "Customer A 72%" for the three months ended
  March 31, 2025 — concentration has fallen materially as Meta became a new large customer
  (same filing discloses a separate ~$21 billion Meta commitment signed March 2026).
  Concentration is trending down, not static at 62%/77%.

---

## 3. Amazon ↔ Anthropic

**Filing:** Amazon.com, Inc., Form 10-K, fiscal year ended December 31, 2025, filed
2026-02-06. CIK 0001018724, accession 0001018724-26-000004.
URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm

### 3.1 Accounting method — explicitly NOT equity method

> "Equity investments in private companies not accounted for under the equity-method, which
> primarily relate to nonvoting preferred stock in Anthropic, are accounted for at cost, with
> adjustments for observable changes in prices or impairments representing Level 3 fair value
> measurements recognized in 'Other income (expense), net' on our consolidated statements of
> operations."

**Verdict:** Amazon's Anthropic stake is **not** equity-method accounted (unlike Microsoft's
OpenAI stake). It is carried at cost with fair-value step-ups/step-downs for "observable price
changes," booked through Other Income (Expense) — the accounting mechanics that produce large,
volatile mark-to-market swings rather than a pro-rata share of Anthropic's reported net
income/loss. Any demo edge modeled as "equity-method Amazon↔Anthropic impact" (paralleling the
Microsoft↔OpenAI edge) would misrepresent the filing; the correct structural label is
"unrealized fair-value gain/loss on a minority equity stake," a different mathematical object
from equity-method income participation.

### 3.2 Investment amounts and running balance

> "From Q3 2023 to Q4 2024, we invested $5.3 billion in convertible notes from Anthropic,
> which are classified as available-for-sale and as Level 3 assets, and as of December 31,
> 2024 had an estimated fair value of approximately $13.8 billion."
>
> "In Q2 2025, we invested $1.3 billion in a new convertible note from Anthropic... In Q3
> 2025, an additional portion of our notes was converted to nonvoting preferred stock, and as
> a result of the conversion a portion of the unrealized gain associated with the notes was
> reclassified and a gain of approximately $2.3 billion was recorded in 'Other income
> (expense), net.' We also recorded an upward adjustment of $7.2 billion to our nonvoting
> preferred stock in 'Other income (expense), net' to reflect observable changes in price. In
> Q4 2025, we invested $1.4 billion in a new convertible note from Anthropic. As of December
> 31, 2025, the amount recorded on our consolidated balance sheet for nonvoting preferred
> stock was approximately $14.8 billion. As of December 31, 2025, the estimated fair value of
> our convertible notes recorded on our consolidated balance sheet was approximately $45.8
> billion..."
>
> Cash-flow statement: "We made cash payments... related to acquisition and other investment
> activity of $7.1 billion and $3.8 billion in 2024 and 2025, which primarily reflect
> investments in convertible notes from Anthropic... including $2.7 billion we invested in
> 2025."

**Verdict:** No specific Amazon↔Anthropic figure currently appears in the demo's own docs
(searched CONTEXT.md, all ADRs, and the implementation plan — none pin a number for this
edge; the task brief's "8B/4B" style figures floated informally were not found in the repo).
This section establishes what a correctly-sourced version of this edge would say, since the
demo may add it later:
- **Cumulative invested in convertible notes:** $5.3B (Q3 2023–Q4 2024) + $1.3B (Q2 2025) +
  $1.4B (Q4 2025) = **$8.0B invested** across all tranches disclosed in the FY2025 10-K.
- **Balance-sheet carrying values as of Dec 31, 2025:** nonvoting preferred stock ≈ $14.8B;
  remaining convertible notes at estimated fair value ≈ $45.8B.
- **Income-statement effect:** a $2.3B reclassification gain (Q3 2025 conversion) + a $7.2B
  fair-value step-up (Q3 2025) + further contribution to a **$15.2 billion net gain in 2025**
  overall (per the MD&A: "The net gain of $15.2 billion in 2025 is primarily from an upward
  adjustment for observable changes in price relating to our nonvoting preferred stock in
  Anthropic, and the reclassification adjustments for the gains on available-for-sale debt
  securities from the portions of our convertible notes investments in Anthropic that were
  converted to nonvoting preferred stock during 2025.")
- These are **unrealized fair-value gains on a minority stake**, not equity-method earnings
  participation — structurally a different object from the Microsoft/OpenAI edge, and should
  be rendered accordingly if added to the graph (closer to "exposure/gain-at-risk," not
  "calculated accounting impact").

---

## Closing summary

| Figure (as used in the demo/ADR 0004) | Verdict | Notes |
|---|---|---|
| MSFT: $13B total OpenAI funding commitments, equity method | **Safe as-is** | Verbatim in FY2025 10-K and reaffirmed in both later 10-Qs. |
| MSFT: ~27% as-converted OpenAI ownership | **Safe, but add a date qualifier** | Verbatim ("approximately 27 percent... as-converted diluted basis"), confirmed in the most recent 10-Q — but it postdates the Oct 28, 2025 recapitalization and uses HLBV equity-method accounting; pre-recap filings disclosed no percentage. Say "as of [date]," not "Microsoft's OpenAI stake" unqualified. |
| MSFT: $3.1B FY26Q1 net-income effect from OpenAI | **Safe as-is, but frame as one quarter, not a run-rate** | Verbatim in the Q1 FY2026 10-Q. A different, larger $4.1B figure for the *same quarter* exists in the Other Income note — don't conflate them. By Q3 FY2026 the same line swung to a +$4.5B gain, netting the nine-month cumulative effect to −$14M — disclose the quarter-specific framing or the number reads as more stable than it is. |
| MSFT: $2.7B illustrative equity-method calc (27% × $10B hypothetical) | **Safe, already correctly labeled hypothetical in ADR 0005** | Confirmed this is analyst arithmetic, not a filed number — keep it visually and textually distinct from the real $3.1B, as ADR 0005 already requires. |
| CoreWeave: $11.9B OpenAI commitment through Oct 2030 | **Safe as-is** | Verbatim in S-1/A and reconfirmed unchanged in the most recent (Q1 2026) 10-Q. Watch for a same-filing false-positive: an unrelated $11.9B real-estate lease commitment exists in the same S-1/A — extraction should require "OpenAI" + "October 2030" co-occurrence. Also note a *second*, additional OpenAI commitment of $6.5B through May 2031 now exists in the latest 10-Q — if presenting "total" OpenAI-CoreWeave exposure as of today, $11.9B alone understates it. |
| CoreWeave: $11.55B figure | **Needs a precise label, not removal** | Real, in the same S-1/A, but the filing never states the $11.9B→$11.55B reconciliation explicitly (we inferred it: $11.9B − $350M OpenAI equity stake ≈ $11.55B). Label it "future revenue net of the OpenAI equity component," not as an independent commitment. |
| CoreWeave: $15.1B RPO (end-2024) | **Safe as-is, label as historical** | Verbatim in the S-1. Already superseded by $30.1B (June 30, 2025) in later filings — fine as a historical anchor, not as "current." |
| CoreWeave: MSFT 35%/62%/77% concentration | **Safe as-is, label as annual (FY2023/FY2024)** | Verbatim in the S-1. Quarterly figures in later 10-Qs (71%/59% for Q2; 45%/20% Customer A/B for the latest quarter, as Meta enters) are different and falling — don't blend annual and quarterly figures. |
| Amazon: Anthropic investment amount | **Not previously specified in the demo — now sourced above** | No figure exists yet in the repo's own docs to verify against. If added: not equity method (explicit in the FY2025 10-K); correct framing is cumulative $8.0B invested in convertible notes, ~$14.8B nonvoting-preferred carrying value and ~$45.8B convertible-note fair value as of Dec 31, 2025, and large ($15.2B in 2025) unrealized-gain swings booked through Other Income (Expense) — a fair-value "exposure/gain" object, not an "equity-method impact" object like the Microsoft/OpenAI edge. |

**Bottom line:** every one of the five specific figures named in ADR 0004's "verification
debt" note (27%, $3.1B, $11.9B, 35/62/77%, $15.1B) is **verbatim-confirmed in a primary SEC
filing** and safe to keep presenting as "solid." The two things that need to change before
the demo ships are (1) attach explicit date/quarter qualifiers to the 27% and $3.1B figures
so they aren't read as timeless constants — both are snapshots that the filings themselves
show moving substantially (27% is post-recap-only; $3.1B's own line item was +$4.5B two
quarters later), and (2) decide how to handle the newly-discovered $6.5B second OpenAI→
CoreWeave commitment and the still-unreconciled $11.55B figure so the extraction pipeline
doesn't silently pick the wrong "$11.9 billion" out of a filing that contains two unrelated
ones.
