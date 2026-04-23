import type { ReactNode } from "react";

export type MetricCardTone = "good" | "medium" | "high" | "neutral";

type MetricCardProps = {
  label: ReactNode;
  value: ReactNode;
  tone?: MetricCardTone;
  valueClassName?: string;
  children?: ReactNode;
};

export function MetricCard({
  label,
  value,
  tone = "neutral",
  valueClassName = "metric-value",
  children,
}: MetricCardProps) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <div className="metric-label">{label}</div>
      <div className={valueClassName}>{value}</div>
      {children}
    </article>
  );
}
