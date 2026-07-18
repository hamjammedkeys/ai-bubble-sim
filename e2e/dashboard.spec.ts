import { expect, test } from "@playwright/test";

test("dashboard opens on the map and runs a shock", async ({ page }) => {
  const unexpectedConsoleErrors: string[] = [];
  const pageErrors: Error[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("Failed to load resource")) {
      unexpectedConsoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => pageErrors.push(error));

  await page.goto("http://127.0.0.1:5173");

  await expect(page.getByText("AI Fragility Map")).toBeVisible();
  await expect(page.getByText("estimated impact under scenario").first()).toBeVisible();
  await page.getByRole("button", { name: "Run shock" }).click();
  await expect(page.getByLabel("AI supply-chain network map")).toBeVisible();
  expect(unexpectedConsoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
