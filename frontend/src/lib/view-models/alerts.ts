import type { DailyFocusItem } from "../api/daily-focus";

export interface AlertGroup {
  date: string;
  items: DailyFocusItem[];
}

export function groupAlertsByDate(items: DailyFocusItem[]): AlertGroup[] {
  const groups: Record<string, DailyFocusItem[]> = {};
  items.forEach((item) => {
    const date = new Date(item.detected_at).toLocaleDateString("zh-CN");
    if (!groups[date]) groups[date] = [];
    groups[date].push(item);
  });
  return Object.entries(groups).map(([date, items]) => ({ date, items }));
}

export function buildAlertStats(items: DailyFocusItem[]) {
  return {
    total: items.length,
    critical: items.filter((i) => i.severity === "critical").length,
    high: items.filter((i) => i.severity === "high").length,
    medium: items.filter((i) => i.severity === "medium").length,
    low: items.filter((i) => i.severity === "low").length,
    pending: items.filter(
      (i) => i.status === "pending" || i.status === "needs_manual_confirmation"
    ).length,
    resolved: items.filter((i) => i.status === "resolved").length,
  };
}
