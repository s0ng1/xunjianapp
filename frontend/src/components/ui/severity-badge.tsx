import type { ReactNode } from "react";

export type SeverityBadgeTone = "critical" | "high" | "medium" | "low" | "info" | "good" | "neutral";

type SeverityBadgeProps = {
  children: ReactNode;
  tone: SeverityBadgeTone;
  className?: "badge" | "status-chip";
};

export function SeverityBadge({ children, tone, className = "badge" }: SeverityBadgeProps) {
  return <span className={`${className} tone-${tone}`}>{children}</span>;
}
