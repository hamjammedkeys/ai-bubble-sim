import { expect, test } from "@playwright/test";

test("dashboard opens on the map and runs a shock", async ({ page }) => {
  const scenarioRequests: unknown[] = [];
  const consoleErrors: string[] = [];
  const pageErrors: Error[] = [];
  await page.route("**/api/scenario/cloud-slowdown", async (route) => {
    scenarioRequests.push(route.request().postDataJSON());
    await route.fulfill({
      contentType: "application/json",
      json: {
        nodes: [
          {
            data: {
              id: "cloud",
              label: "Cloud Platform",
              sectorGroup: "Cloud",
              revenue: 1000,
              revenueLoss: 300,
              stressStatus: "critical"
            }
          },
          {
            data: {
              id: "supplier",
              label: "AI Supplier",
              sectorGroup: "Semiconductors",
              revenue: 500,
              revenueLoss: 120,
              stressStatus: "stressed"
            }
          }
        ],
        edges: [
          {
            data: {
              id: "cloud-supplier",
              source: "cloud",
              target: "supplier",
              annualFlowBase: 400,
              confidenceScore: 0.8,
              estimateMethod: "inferred"
            }
          }
        ],
        pulses: [
          {
            relationshipId: "cloud-supplier",
            source: "cloud",
            target: "supplier",
            roundIndex: 1,
            revenueLoss: 120
          }
        ],
        summary: {
          scenarioLanguage: "estimated impact under scenario",
          totalRevenueLost: 420,
          stressedCompanyCount: 2
        }
      }
    });
  });
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => pageErrors.push(error));

  await page.goto("http://127.0.0.1:5173");

  await expect(page.getByText("AI Fragility Map")).toBeVisible();
  await expect(page.locator("header").getByText("estimated impact under scenario")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Scenario Results" }).locator("..").getByText("estimated impact under scenario")
  ).toBeVisible();
  await expect.poll(() => scenarioRequests).toHaveLength(1);
  await page.getByRole("button", { name: "Run shock" }).click();
  await expect(page.getByLabel("AI supply-chain network map")).toBeVisible();
  await expect.poll(() => scenarioRequests).toHaveLength(2);
  expect(scenarioRequests).toEqual([
    {
      shock_percentage: 0.3,
      pass_through_rate: 0.8,
      propagation_factor: 0.5,
      max_rounds: 3
    },
    {
      shock_percentage: 0.3,
      pass_through_rate: 0.8,
      propagation_factor: 0.5,
      max_rounds: 3
    }
  ]);
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
