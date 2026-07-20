import type { ComponentPropsWithoutRef, ReactNode } from "react";

export type TerminalTone = "neutral" | "impact" | "exposure" | "candidate" | "pass";

const toneClassName: Record<TerminalTone, string> = {
  neutral: "",
  impact: "terminal-tone-impact",
  exposure: "terminal-tone-exposure",
  candidate: "terminal-tone-candidate",
  pass: "terminal-tone-pass",
};

function joinClassNames(...classNames: Array<string | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

type TonedProps = {
  tone?: TerminalTone;
};

export type TerminalLabelProps = ComponentPropsWithoutRef<"span"> & TonedProps;

export function TerminalLabel({ className, tone = "neutral", ...props }: TerminalLabelProps) {
  return (
    <span
      className={joinClassNames("terminal-label", toneClassName[tone], className)}
      {...props}
    />
  );
}

export type TerminalMetricProps = Omit<ComponentPropsWithoutRef<"div">, "children"> &
  TonedProps & {
    label: ReactNode;
    value: string | null;
  };

export function TerminalMetric({
  className,
  label,
  tone = "neutral",
  value,
  ...props
}: TerminalMetricProps) {
  return (
    <div className={joinClassNames("terminal-metric", toneClassName[tone], className)} {...props}>
      <TerminalLabel>{label}</TerminalLabel>
      <div className="num">{value ?? "—"}</div>
    </div>
  );
}

export type TerminalButtonProps = ComponentPropsWithoutRef<"button"> & TonedProps;

export function TerminalButton({ className, tone = "neutral", ...props }: TerminalButtonProps) {
  return (
    <button
      className={joinClassNames("terminal-button", "terminal-focus", toneClassName[tone], className)}
      {...props}
    />
  );
}

export type TerminalPanelProps = ComponentPropsWithoutRef<"div"> & TonedProps;

export function TerminalPanel({ className, tone = "neutral", ...props }: TerminalPanelProps) {
  return (
    <div
      className={joinClassNames("terminal-panel", toneClassName[tone], className)}
      {...props}
    />
  );
}

export type TerminalStatusProps = ComponentPropsWithoutRef<"span"> & TonedProps;

export function TerminalStatus({ className, tone = "neutral", ...props }: TerminalStatusProps) {
  return (
    <span
      className={joinClassNames("num", "terminal-label", toneClassName[tone], className)}
      {...props}
    />
  );
}
