import { AlertsPageClient } from "@/components/alerts-page-client";
import { DashboardShell } from "@/components/dashboard-shell";
import {
  fetchAssets,
  fetchLinuxInspections,
  fetchSwitchInspections,
} from "@/lib/api";
import { buildAlertsList } from "@/lib/inspection-view";

export default async function AlertsPage() {
  const [assetsResult, linuxResult, switchResult] = await Promise.allSettled([
    fetchAssets(),
    fetchLinuxInspections(),
    fetchSwitchInspections(),
  ]);

  const assets = assetsResult.status === "fulfilled" ? assetsResult.value : [];
  const linuxInspections = linuxResult.status === "fulfilled" ? linuxResult.value : [];
  const switchInspections = switchResult.status === "fulfilled" ? switchResult.value : [];
  const alerts = buildAlertsList(assets, linuxInspections, switchInspections);

  return (
    <DashboardShell
      activePath="/alerts"
      badge="告警中心"
      title="告警列表"
      description="当前仅展示真实巡检失败项派生的告警。"
    >
      <AlertsPageClient alerts={alerts} />
    </DashboardShell>
  );
}
