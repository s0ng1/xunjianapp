import { DashboardShell } from "@/components/layout/dashboard-shell";
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
  const failedCount = inspections.filter((inspection) => inspection.status === "failed").length;
  const partialCount = inspections.filter((inspection) => inspection.status === "partial").length;
  const baselineCount = inspections.filter((inspection) => inspection.type === "baseline").length;

  return (
    <DashboardShell
      activePath="/inspections"
      badge="巡检留痕"
      title="巡检历史"
      description="把 Linux、交换机、端口扫描和基线执行结果放在同一时间线中，便于追踪每次动作的结果。"
      summary={
        inspections.length > 0
          ? `当前保留 ${inspections.length} 条真实执行记录，失败 ${failedCount} 条，部分异常 ${partialCount} 条。`
          : "当前还没有可展示的真实巡检、扫描或基线执行记录。"
      }
      stats={[
        {
          label: "执行记录",
          value: String(inspections.length),
          conclusion: "覆盖巡检、扫描与基线执行",
          tone: inspections.length > 0 ? "info" : "medium",
          statusText: inspections.length > 0 ? "有记录" : "空",
        },
        {
          label: "失败",
          value: String(failedCount),
          conclusion: failedCount > 0 ? "需要复核连通性和凭据配置" : "执行失败项已清空",
          tone: failedCount > 0 ? "critical" : "normal",
          statusText: failedCount > 0 ? "异常" : "稳定",
        },
        {
          label: "部分异常",
          value: String(partialCount),
          conclusion: partialCount > 0 ? "存在基线失败或扫描异常" : "没有部分异常记录",
          tone: partialCount > 0 ? "medium" : "normal",
          statusText: partialCount > 0 ? "需关注" : "正常",
        },
        {
          label: "基线执行",
          value: String(baselineCount),
          conclusion: "可在 Baseline 页面查看规则维度汇总",
          tone: "low",
          statusText: "规则视角",
        },
      ]}
    >
      <InspectionsPageClient inspections={inspections} />
    </DashboardShell>
  );
}
