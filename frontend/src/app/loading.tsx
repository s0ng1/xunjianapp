import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function Loading() {
  return (
    <DashboardShell
      activePath="/"
      layout="workspace"
      badge="首页 / 工作台"
      title="今日工作台"
      description="先看今日摘要，再判断待处理风险、变化和重点设备。"
      summary="正在汇总今天最重要的处理方向。"
      actions={
        <div className="page-meta-stack">
          <span className="page-meta-pill">正在刷新</span>
          <span className="page-meta-note">首页会在聚合数据返回后展示最新结论。</span>
        </div>
      }
      stats={[
        { label: "今日必须处理", value: "--", conclusion: "正在读取高危待处理项", tone: "info", statusText: "加载中" },
        { label: "今日变化", value: "--", conclusion: "正在汇总今日新增变化", tone: "info", statusText: "加载中" },
        { label: "本周安排", value: "--", conclusion: "正在汇总本周待编排事项", tone: "info", statusText: "加载中" },
        { label: "人工确认", value: "--", conclusion: "正在读取待人工确认项", tone: "info", statusText: "加载中" },
      ]}
    >
      <section className="panel-card">
        <div className="skeleton-block" />
        <div className="skeleton-block short" />
        <div className="skeleton-table" />
      </section>
    </DashboardShell>
  );
}
