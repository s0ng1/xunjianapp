import { DashboardShell } from "@/components/dashboard-shell";
import { InspectionsPageClient } from "@/components/inspections-page-client";
import {
  fetchAssets,
  fetchBaselineRuns,
  fetchLinuxInspections,
  fetchPortScans,
  fetchSwitchInspections,
} from "@/lib/api";
import { buildInspectionHistoryList } from "@/lib/inspection-view";

export default async function InspectionsPage() {
  const [assetsResult, linuxResult, switchResult, portScanResult, baselineResult] = await Promise.allSettled([
    fetchAssets(),
    fetchLinuxInspections(),
    fetchSwitchInspections(),
    fetchPortScans(),
    fetchBaselineRuns(),
  ]);

  const assets = assetsResult.status === "fulfilled" ? assetsResult.value : [];
  const linuxInspections = linuxResult.status === "fulfilled" ? linuxResult.value : [];
  const switchInspections = switchResult.status === "fulfilled" ? switchResult.value : [];
  const portScans = portScanResult.status === "fulfilled" ? portScanResult.value : [];
  const baselineRuns = baselineResult.status === "fulfilled" ? baselineResult.value : [];
  const inspections = buildInspectionHistoryList(
    assets,
    linuxInspections,
    switchInspections,
    portScans,
    baselineRuns,
  );

  return (
    <DashboardShell
      activePath="/inspections"
      badge="巡检留痕"
      title="巡检记录页"
      description="只展示真实巡检、扫描和基线执行记录。"
    >
      <InspectionsPageClient inspections={inspections} />
    </DashboardShell>
  );
}
