import { SchedulesPageClient } from "@/components/schedules-page-client";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function SchedulesPage() {
  return (
    <DashboardShell
      activePath="/schedules"
      badge="任务调度"
      title="任务调度"
      description="把 SSH 测试、巡检、扫描、基线检查编排成周期任务"
    >
      <SchedulesPageClient />
    </DashboardShell>
  );
}
