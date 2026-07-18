import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

describe("App", () => {
  it("opens on the working AI fragility map", async () => {
    render(<App />);

    expect(await screen.findByText("AI Fragility Map")).toBeTruthy();
    expect(screen.getByText("estimated impact under scenario")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Run shock" })).toBeTruthy();
  });
});
