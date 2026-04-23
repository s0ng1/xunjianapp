import { fetchFromApi } from "./client";
import type { BaselineCheckResult } from "./inspections";

export type BaselineRun = {
  asset_id: number | null;
  inspection_id: number;
  source_type: "linux_inspection" | "switch_inspection";
  device_type: string;
  ip: string;
  username: string;
  vendor: string | null;
  success: boolean;
  message: string;
  baseline_results: BaselineCheckResult[];
  created_at: string;
};

export type LinuxInspectionPayload = {
  ip: string;
  username: string;
  password: string;
};

export type SwitchInspectionPayload = LinuxInspectionPayload & {
  vendor: string;
};

export const baselineApi = {
  list: () => fetchFromApi<BaselineRun[]>("/api/v1/baseline-checks"),

  runLinux: (payload: LinuxInspectionPayload) =>
    fetchFromApi<BaselineRun>("/api/v1/baseline-checks/linux/run", { method: "POST", body: payload }),

  runSwitch: (payload: SwitchInspectionPayload) =>
    fetchFromApi<BaselineRun>("/api/v1/baseline-checks/switch/run", { method: "POST", body: payload }),

  rerunLinux: (inspectionId: number) =>
    fetchFromApi<BaselineRun>(`/api/v1/baseline-checks/linux/${inspectionId}/rerun`, { method: "POST" }),

  rerunSwitch: (inspectionId: number) =>
    fetchFromApi<BaselineRun>(`/api/v1/baseline-checks/switch/${inspectionId}/rerun`, { method: "POST" }),
};
