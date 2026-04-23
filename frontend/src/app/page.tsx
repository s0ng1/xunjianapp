import type { FocusRiskOverviewData } from "@/components/focus-risk-overview";
import { DailyFocusPanel } from "@/components/daily-focus-panel";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { StatePanel } from "@/components/state-panel";
import {
  fetchDailyFocus,
  fetchLinuxInspections,
  fetchSwitchInspections,
  type BaselineCheckResult,
  type DailyFocus,
  type LinuxInspection,
  type SwitchInspection,
} from "@/lib/api";

export default async function HomePage() {
  try {
    const focus = await fetchDailyFocus();
    const inspectionResults = await Promise.allSettled([fetchLinuxInspections(), fetchSwitchInspections()]);
    const linuxInspections = inspectionResults[0].status === "fulfilled" ? inspectionResults[0].value : [];
    const switchInspections = inspectionResults[1].status === "fulfilled" ? inspectionResults[1].value : [];
    const overview = buildFocusRiskOverview(focus, linuxInspections, switchInspections);
    const stats = buildWorkspaceStats(focus);

    return (
      <DashboardShell
        activePath="/"
        layout="workspace"
        badge="首页 / 工作台"
        title="今日工作台"
        description="先看今日摘要，再判断待处理风险、变化和重点设备。"
        summary={focus.today_summary}
        actions={
          <div className="page-meta-stack">
            <span className="page-meta-pill">{`基准日 ${focus.reference_date}`}</span>
            <span className="page-meta-note">结论来自最新巡检、端口扫描与基线结果汇总。</span>
          </div>
        }
        stats={stats}
      >
        <DailyFocusPanel focus={focus} overview={overview} />
      </DashboardShell>
    );
  } catch (error) {
    const description =
      error instanceof Error ? error.message : "当前无法获取每日工作重点聚合结果。";

    return (
      <DashboardShell
        activePath="/"
        layout="workspace"
        badge="首页 / 工作台"
        title="今日工作台"
        description="先看今日摘要，再判断待处理风险、变化和重点设备。"
      >
        <StatePanel tone="error" title="每日工作重点加载失败" description={description} />
      </DashboardShell>
    );
  }
}

function buildWorkspaceStats(focus: DailyFocus) {
  const manualConfirmationCount = countManualConfirmationItems(focus);

  return [
    {
      label: "今日必须处理",
      value: String(focus.summary.must_handle_count),
      conclusion:
        focus.summary.must_handle_count > 0
          ? `需优先闭环 ${focus.summary.must_handle_count} 项高危问题`
          : "当前无高危未处理项",
      tone: focus.summary.must_handle_count > 0 ? ("critical" as const) : ("normal" as const),
      statusText: focus.summary.must_handle_count > 0 ? "需立刻处理" : "当前稳定",
    },
    {
      label: "今日变化",
      value: String(focus.summary.today_changes_count),
      conclusion:
        focus.summary.today_changes_count > 0
          ? `今天出现 ${focus.summary.today_changes_count} 项新增变化`
          : "今天未发现新增变化",
      tone: focus.summary.today_changes_count > 0 ? ("medium" as const) : ("normal" as const),
      statusText: focus.summary.today_changes_count > 0 ? "存在变化" : "变化平稳",
    },
    {
      label: "本周安排",
      value: String(focus.summary.weekly_plan_count),
      conclusion:
        focus.summary.weekly_plan_count > 0
          ? `本周仍有 ${focus.summary.weekly_plan_count} 项待编排事项`
          : "本周暂无积压安排",
      tone: focus.summary.weekly_plan_count > 0 ? ("medium" as const) : ("normal" as const),
      statusText: focus.summary.weekly_plan_count > 0 ? "需排期" : "排期清空",
    },
    {
      label: "人工确认",
      value: String(manualConfirmationCount),
      conclusion:
        manualConfirmationCount > 0 ? `需补充 ${manualConfirmationCount} 项人工核查结论` : "当前无待人工确认项",
      tone: manualConfirmationCount > 0 ? ("medium" as const) : ("normal" as const),
      statusText: manualConfirmationCount > 0 ? "待核查" : "无需确认",
    },
  ];
}

function buildFocusRiskOverview(
  focus: DailyFocus,
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
): FocusRiskOverviewData {
  return {
    distribution: buildRiskDistribution(linuxInspections, switchInspections),
    topDevices: focus.priority_devices
      .map((device) => ({
        name: device.asset_name || device.asset_ip,
        ip: device.asset_ip,
        total:
          device.high_count +
          device.medium_count +
          device.today_changes_count +
          device.needs_manual_confirmation_count,
        high: device.high_count,
        medium: device.medium_count,
        changes: device.today_changes_count,
        manual: device.needs_manual_confirmation_count,
      }))
      .sort((left, right) => {
        if (right.total !== left.total) {
          return right.total - left.total;
        }
        if (right.high !== left.high) {
          return right.high - left.high;
        }
        return right.medium - left.medium;
      })
      .slice(0, 5),
    trend: buildRiskTrend(linuxInspections, switchInspections),
  };
}

function buildRiskDistribution(
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
): FocusRiskOverviewData["distribution"] {
  const latestInspections = new Map<string, LinuxInspection | SwitchInspection>();

  for (const inspection of [...linuxInspections, ...switchInspections]) {
    const sourceKey = "vendor" in inspection ? "switch" : "linux";
    const currentKey = `${sourceKey}:${inspection.ip}`;
    const previous = latestInspections.get(currentKey);
    if (!previous || new Date(inspection.created_at).getTime() > new Date(previous.created_at).getTime()) {
      latestInspections.set(currentKey, inspection);
    }
  }

  const counts = { high: 0, medium: 0, low: 0, normal: 0 };
  for (const inspection of latestInspections.values()) {
    for (const result of inspection.baseline_results) {
      const status = result.status.trim().toLowerCase();
      const riskLevel = result.risk_level.trim().toLowerCase();
      if (status === "pass") {
        counts.normal += 1;
        continue;
      }
      if (status !== "fail") {
        continue;
      }
      if (riskLevel === "high") {
        counts.high += 1;
      } else if (riskLevel === "medium") {
        counts.medium += 1;
      } else if (riskLevel === "low") {
        counts.low += 1;
      }
    }
  }

  return [
    { key: "high", label: "高危", value: counts.high },
    { key: "medium", label: "中危", value: counts.medium },
    { key: "low", label: "低危", value: counts.low },
    { key: "normal", label: "正常", value: counts.normal },
  ];
}

function buildRiskTrend(
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
): FocusRiskOverviewData["trend"] {
  const formatter = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai" });
  const shortFormatter = new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    timeZone: "Asia/Shanghai",
  });
  const dayBuckets = createRecentDateKeys(7, formatter);
  const counts = new Map<string, number>(dayBuckets.map((dayKey) => [dayKey, 0]));

  for (const inspection of [...linuxInspections, ...switchInspections]) {
    const dayKey = formatter.format(new Date(inspection.created_at));
    if (!counts.has(dayKey)) {
      continue;
    }
    const highFailCount = inspection.baseline_results.reduce((sum, result) => {
      return sum + (isHighFail(result) ? 1 : 0);
    }, 0);
    counts.set(dayKey, (counts.get(dayKey) ?? 0) + highFailCount);
  }

  return dayBuckets.map((dayKey) => ({
    date: dayKey,
    shortLabel: shortFormatter.format(new Date(`${dayKey}T00:00:00+08:00`)),
    highFailCount: counts.get(dayKey) ?? 0,
  }));
}

function createRecentDateKeys(days: number, formatter: Intl.DateTimeFormat): string[] {
  const keys: string[] = [];
  const today = new Date();

  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const current = new Date(today);
    current.setDate(today.getDate() - offset);
    keys.push(formatter.format(current));
  }

  return keys;
}

function countManualConfirmationItems(focus: DailyFocus): number {
  const items = [
    ...focus.today_must_handle.flatMap((group) => group.items),
    ...focus.today_changes,
    ...focus.weekly_plan,
  ];

  return items.reduce((count, item) => {
    return count + (item.status === "needs_manual_confirmation" ? 1 : 0);
  }, 0);
}

function isHighFail(result: BaselineCheckResult): boolean {
  return result.status.trim().toLowerCase() === "fail" && result.risk_level.trim().toLowerCase() === "high";
}
