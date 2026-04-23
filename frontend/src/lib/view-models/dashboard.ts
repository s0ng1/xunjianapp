import type { Asset } from "../api/assets";
import type { LinuxInspection, SwitchInspection } from "../api/inspections";
import type { BaselineRun } from "../api/baseline";

export interface DashboardStats {
  totalAssets: number;
  activeInspections: number;
  criticalAlerts: number;
  baselinePassRate: number;
  totalInspections: number;
  passedInspections: number;
}

export function buildDashboardStats(data: {
  assets: Asset[];
  linuxInspections: LinuxInspection[];
  switchInspections: SwitchInspection[];
  baselineRuns: BaselineRun[];
}): DashboardStats {
  const running = [...data.linuxInspections, ...data.switchInspections].filter(
    (i) => i.success === false || !i.created_at
  );
  const passed = data.baselineRuns.filter((r) => r.success === true).length;
  const passRate = data.baselineRuns.length > 0 ? Math.round((passed / data.baselineRuns.length) * 100) : 0;

  return {
    totalAssets: data.assets.length,
    activeInspections: running.length,
    criticalAlerts: 0,
    baselinePassRate: passRate,
    totalInspections: data.baselineRuns.length,
    passedInspections: passed,
  };
}
