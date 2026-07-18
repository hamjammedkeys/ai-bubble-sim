import { expect, test } from "@playwright/test";

const scenarioPayload = {
  scenario: {
    incrementalGaapLoss: 10_000_000_000,
    creditStatus: "severe_distress",
    defaultStatus: "not_defaulted",
    language: "calculated Impact plus activated Exposure; downstream loss not identifiable"
  },
  nodes: [],
  edges: [
    {
      relationshipId: "openai-msft",
      source: "openai",
      target: "msft",
      structureType: "equity_method",
      tier: "solid_red",
      resultKind: "impact",
      value: -2_700_000_000,
      basis: "equity-method share of stated GAAP loss",
      provenance: {},
      sourceAccession: "openai-10k-2025"
    },
    {
      relationshipId: "openai-coreweave",
      source: "openai",
      target: "coreweave",
      structureType: "take_or_pay",
      tier: "solid_orange",
      resultKind: "exposure",
      value: 11_900_000_000,
      basis: "take-or-pay contract envelope activated",
      provenance: {},
      sourceAccession: "coreweave-s1a-2025"
    },
    {
      relationshipId: "openai-coreweave-realized-loss",
      source: "openai",
      target: "coreweave",
      structureType: "take_or_pay",
      tier: "dashed_amber",
      resultKind: "realized_loss_unidentifiable",
      value: null,
      basis: "EAD, PD, LGD, and timing are undisclosed",
      provenance: {},
      sourceAccession: "coreweave-s1a-2025"
    }
  ],
  ranking: []
};

const reviewCandidate = {
  candidateId: "candidate-1",
  sourceId: "msft-filing",
  sourceAccession: "acc-1",
  sourceCompanyId: "msft",
  targetCompanyId: "coreweave",
  relationshipType: "take_or_pay",
  quotedText: "Reported commitment.",
  numericToken: "$4 billion",
  value: 4_000_000_000,
  unit: "USD",
  period: "through 2030",
  supportedRule: "reported purchase commitment envelope",
  unsupportedInference: "counterparty mapping awaits review",
  status: "proposed"
};

test("hero compound credit event preserves evidence grammar", async ({ page }) => {
  const scenarioRequests: unknown[] = [];
  const legacyRequests: string[] = [];
  let rejected = false;
  const auditLog = [
    {
      auditId: "audit-1",
      candidateId: "candidate-1",
      fromStatus: "proposed",
      toStatus: "rejected",
      reviewerId: "dashboard-reviewer",
      reason: "Rejected from dashboard",
      verificationValid: true,
      createdAt: "2026-07-18T00:00:00Z"
    }
  ];

  await page.route("**/api/scenario/cloud-slowdown", async (route) => {
    legacyRequests.push(route.request().url());
    await route.abort();
  });
  await page.route("**/api/v2/scenario/compound-credit-event", async (route) => {
    scenarioRequests.push(route.request().postDataJSON());
    await route.fulfill({
      contentType: "application/json",
      json: { ...scenarioPayload, reviewCandidates: [reviewCandidate], auditLog: [] }
    });
  });
  await page.route("**/api/v2/review/candidates", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        ...scenarioPayload,
        reviewCandidates: rejected ? [] : [reviewCandidate],
        auditLog: rejected ? auditLog : []
      }
    });
  });
  await page.route("**/api/v2/review/candidate-1/reject", async (route) => {
    rejected = true;
    await route.fulfill({
      contentType: "application/json",
      json: { ...scenarioPayload, reviewCandidates: [], auditLog }
    });
  });

  await page.goto("/");
  await expect(page.getByRole("button", { name: "Run compound credit event" })).toBeVisible();
  await page.getByRole("button", { name: "Run compound credit event" }).click();
  await expect(page.getByText("Observed shock: $10.0B incremental GAAP loss")).toBeVisible();
  await expect(page.getByText("Credit status: severe distress · Default status: not defaulted")).toBeVisible();
  await expect(page.getByText("Calculated Impact", { exact: true })).toBeVisible();
  await expect(page.getByText("Activated Exposure", { exact: true })).toBeVisible();
  await expect(page.getByText("Realized loss: not identifiable", { exact: true })).toBeVisible();
  await expect(page.getByText("Pending human review", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Reject candidate" }).click();
  const auditLogRegion = page.getByRole("region", { name: "Audit log" });
  await expect(auditLogRegion.getByRole("heading", { name: "Audit log" })).toBeVisible();
  await expect(auditLogRegion.getByText("Rejected from dashboard")).toBeVisible();

  expect(scenarioRequests).toContainEqual({
    incremental_gaap_loss: 10_000_000_000,
    credit_status: "severe_distress",
    default_status: "not_defaulted"
  });
  expect(legacyRequests).toEqual([]);
});
