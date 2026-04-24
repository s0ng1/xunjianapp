import { fetchFromApi } from "./client";

export type TaskType = "ssh_test" | "linux_inspection" | "switch_inspection" | "port_scan" | "baseline_check";
export type ScheduleType = "interval" | "cron";

export interface ScheduledTask {
  id: number;
  name: string;
  task_type: TaskType;
  asset_id: number | null;
  schedule_type: ScheduleType;
  interval_seconds: number | null;
  cron_expression: string | null;
  timezone: string;
  params: Record<string, any>;
  is_enabled: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string | null;
  last_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduledTaskCreate {
  name: string;
  task_type: TaskType;
  asset_id?: number | null;
  schedule_type: ScheduleType;
  interval_seconds?: number | null;
  cron_expression?: string | null;
  timezone?: string;
  params?: Record<string, any>;
  is_enabled?: boolean;
}

export interface ScheduledTaskUpdate {
  name?: string | null;
  schedule_type?: ScheduleType | null;
  interval_seconds?: number | null;
  cron_expression?: string | null;
  timezone?: string | null;
  params?: Record<string, any> | null;
  is_enabled?: boolean | null;
}

export interface ScheduledTaskTriggerResponse {
  success: boolean;
  message: string;
  task_id: number;
}

export async function createScheduledTask(data: ScheduledTaskCreate): Promise<ScheduledTask> {
  return fetchFromApi<ScheduledTask>("/api/scheduled-tasks", { method: "POST", body: data });
}

export async function listScheduledTasks(filters?: {
  task_type?: TaskType;
  asset_id?: number;
  is_enabled?: boolean;
}): Promise<ScheduledTask[]> {
  const params = new URLSearchParams();
  if (filters?.task_type) params.set("task_type", filters.task_type);
  if (filters?.asset_id) params.set("asset_id", String(filters.asset_id));
  if (filters?.is_enabled !== undefined) params.set("is_enabled", String(filters.is_enabled));
  const query = params.toString();
  return fetchFromApi<ScheduledTask[]>(`/api/scheduled-tasks${query ? `?${query}` : ""}`);
}

export async function getScheduledTask(taskId: number): Promise<ScheduledTask> {
  return fetchFromApi<ScheduledTask>(`/api/scheduled-tasks/${taskId}`);
}

export async function updateScheduledTask(taskId: number, data: ScheduledTaskUpdate): Promise<ScheduledTask> {
  return fetchFromApi<ScheduledTask>(`/api/scheduled-tasks/${taskId}`, { method: "PATCH", body: data });
}

export async function deleteScheduledTask(taskId: number): Promise<void> {
  return fetchFromApi<void>(`/api/scheduled-tasks/${taskId}`, { method: "DELETE" });
}

export async function triggerScheduledTask(taskId: number): Promise<ScheduledTaskTriggerResponse> {
  return fetchFromApi<ScheduledTaskTriggerResponse>(`/api/scheduled-tasks/${taskId}/trigger`, { method: "POST" });
}

export const scheduledTasksApi = {
  create: createScheduledTask,
  list: listScheduledTasks,
  get: getScheduledTask,
  update: updateScheduledTask,
  delete: deleteScheduledTask,
  trigger: triggerScheduledTask,
};
