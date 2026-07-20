import { Children, isValidElement, type ComponentProps, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { ChatScenarioCardModel } from "../lib/chat-actions";
import { ChatScenarioCard } from "./chat-scenario-card";
import { TerminalButton } from "./terminal";

const readyModel: ChatScenarioCardModel = {
  scenarioId: "scenario-1",
  status: "ready",
  name: "OpenAI shock",
  originEntity: "OpenAI",
  magnitude: 10,
  unit: "usd_billions",
};

const completeModel: ChatScenarioCardModel = {
  ...readyModel,
  status: "complete",
  totals: {
    impact_total: 2.7,
    exposure_total: 36.8,
    unresolved_count: 3,
  },
  run: { results: [], totals: { impact_total: 2.7, exposure_total: 36.8, unresolved_count: 3 } },
};

describe("ChatScenarioCard", () => {
  it("renders ready scenario details and a square native Run button", () => {
    const html = renderCard(readyModel);

    expect(html).toContain("READY");
    expect(html).toContain("OpenAI shock");
    expect(html).toContain("OpenAI");
    expect(html).toContain("$10.0B");
    expect(html).toMatch(/<button[^>]*type="button"[^>]*>Run scenario<\/button>/);
    expect(html).toContain("border-radius:0");
  });

  it("passes the ready scenario ID to onRun", () => {
    const onRun = vi.fn();
    const card = ChatScenarioCard({
      model: readyModel,
      onRun,
      onView: () => undefined,
    });

    primaryButton(card).props.onClick?.({} as never);

    expect(onRun).toHaveBeenCalledWith("scenario-1");
  });

  it("disables only the ready action while that card is running", () => {
    const html = renderCard(readyModel, { running: true });

    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Running…<\/button>/);
    expect(html).toContain("OpenAI shock");
  });

  it("renders a card-level run failure as an alert without hiding details", () => {
    const html = renderCard(readyModel, { error: "Scenario run failed — request rejected" });

    expect(html).toContain('role="alert"');
    expect(html).toContain("Scenario run failed — request rejected");
    expect(html).toContain("OpenAI shock");
    expect(html).toContain("Run scenario");
  });

  it("renders complete totals without inventing currency or scale", () => {
    const html = renderCard({
      ...completeModel,
      magnitude: 10,
      unit: "usd_millions",
      totals: { ...completeModel.totals, impact_total: 1_234.5 },
    });

    expect(html).toContain("RUN COMPLETE");
    expect(html).toContain("$10.0M");
    expect(html).toContain("1,234.5");
    expect(html).toContain(">36.8<");
    expect(html).toContain(">3<");
    expect(html).not.toContain("$1,234.5");
    expect(html).not.toContain("$36.8");
    expect(html).not.toContain("36.8B");
    expect(html).toMatch(/<button[^>]*type="button"[^>]*>View on graph<\/button>/);
    expect(html).not.toContain("Run scenario");
  });

  it("passes the complete scenario ID and run snapshot to onView", () => {
    const onView = vi.fn();
    const card = ChatScenarioCard({
      model: completeModel,
      onRun: () => undefined,
      onView,
    });

    primaryButton(card).props.onClick?.({} as never);

    expect(onView).toHaveBeenCalledWith("scenario-1", completeModel.run);
  });

  it("does not invent a currency or scale for unknown or absent magnitude units", () => {
    const unknown = renderCard({ ...readyModel, magnitude: 12.5, unit: "widgets" });
    const absent = renderCard({ ...readyModel, magnitude: 12.5, unit: null });

    expect(unknown).toContain("12.5 widgets");
    expect(absent).toContain(">12.5<");
    expect(absent).not.toContain("$12.5");
  });
});

function renderCard(
  model: ChatScenarioCardModel,
  props: Partial<Pick<ComponentProps<typeof ChatScenarioCard>, "running" | "error">> = {},
) {
  return renderToStaticMarkup(
    <ChatScenarioCard
      model={model}
      onRun={() => undefined}
      onView={() => undefined}
      {...props}
    />,
  );
}

function primaryButton(node: ReactNode): ReactElement<ComponentProps<typeof TerminalButton>> {
  if (isValidElement(node)) {
    if (node.type === TerminalButton) {
      return node as ReactElement<ComponentProps<typeof TerminalButton>>;
    }

    for (const child of Children.toArray((node.props as { children?: ReactNode }).children)) {
      try {
        return primaryButton(child);
      } catch {
        // Continue through the rendered component tree.
      }
    }
  }

  throw new Error("Expected a terminal button");
}
