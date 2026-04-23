import { AlertsPageClient } from "@/components/alerts-page-client";
import { DashboardShell } from "@/components/layout/dashboard-shell";
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
  const highCount = alerts.filter((alert) => alert.severity === "high").length;
  const mediumCount = alerts.filter((alert) => alert.severity === "medium").length;

  return (
    <DashboardShell
      activePath="/alerts"
      badge="告警中心"
      title="告警列表"
      description="按检出时间、资产与严重程度聚合真实巡检失败项，优先处理高危和持续暴露问题。"
      summary={
        alerts.length > 0
          ? `当前共 ${alerts.length} 条未处理告警，其中高危 ${highCount} 条、中危 ${mediumCount} 条。`
          : "当前没有由最新巡检派生出的未处理告警。"
      }
      stats={[
        {
          label: "未处理告警",
          value: String(alerts.length),
          conclusion: alerts.length > 0 ? "需要按严重程度进入处置队列" : "告警队列为空",
          tone: alerts.length > 0 ? "medium" : "normal",
          statusText: alerts.length > 0 ? "待处理" : "稳定",
        },
        {
          label: "高危",
          value: String(highCount),
          conclusion: highCount > 0 ? "优先核对资产与基线证据" : "当前无高危告警",
          tone: highCount > 0 ? "critical" : "normal",
          statusText: highCount > 0 ? "优先" : "清空",
        },
        {
          label: "中危",
          value: String(mediumCount),
          conclusion: mediumCount > 0 ? "纳入本周清理节奏" : "当前无中危告警",
          tone: mediumCount > 0 ? "medium" : "normal",
          statusText: mediumCount > 0 ? "排期" : "清空",
        },
      ]}
    >
      <AlertsPageClient alerts={alerts} />
    </DashboardShell>
  );
}
