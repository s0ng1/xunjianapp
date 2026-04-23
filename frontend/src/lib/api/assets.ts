import { fetchFromApi } from "./client";

export type Asset = {
  id: number;
  ip: string;
  type: string;
  name: string;
  connection_type: string;
  port: number;
  username: string | null;
  vendor: string | null;
  credential_id: number | null;
  credential_configured: boolean;
  is_enabled: boolean;
  created_at: string;
};

export type AssetCreatePayload = {
  ip: string;
  type: string;
  name: string;
  connection_type?: string;
  port?: number;
  username?: string | null;
  vendor?: string | null;
  credential_password?: string;
  is_enabled?: boolean;
};

export type AssetUpdatePayload = {
  name?: string;
  connection_type?: string;
  port?: number;
  username?: string | null;
  vendor?: string | null;
  credential_password?: string;
  is_enabled?: boolean;
};

export const assetsApi = {
  list: () => fetchFromApi<Asset[]>("/api/v1/assets"),

  get: (id: number) => fetchFromApi<Asset>(`/api/v1/assets/${id}`),

  create: (payload: AssetCreatePayload) =>
    fetchFromApi<Asset>("/api/v1/assets", { method: "POST", body: payload }),

  update: (id: number, payload: AssetUpdatePayload) =>
    fetchFromApi<Asset>(`/api/v1/assets/${id}`, { method: "PATCH", body: payload }),

  delete: (id: number) =>
    fetchFromApi<void>(`/api/v1/assets/${id}`, { method: "DELETE" }),

  sshTest: (assetId: number) =>
    fetchFromApi<SSHTestResult>(`/api/v1/assets/${assetId}/ssh-test`, { method: "POST" }),

  portScan: (assetId: number, payload: { ports: number[] }) =>
    fetchFromApi<PortScanResult>(`/api/v1/assets/${assetId}/port-scan`, { method: "POST", body: payload }),

  inspect: (assetId: number) =>
    fetchFromApi<BaselineRun>(`/api/v1/assets/${assetId}/inspect`, { method: "POST" }),

  baseline: (assetId: number) =>
    fetchFromApi<BaselineRun>(`/api/v1/assets/${assetId}/baseline`, { method: "POST" }),
};

// Re-export shared types used by assets
export type SSHTestResult = {
  success: boolean;
  message: string;
};

export type PortScanResult = {
  id: number;
  asset_id: number | null;
  ip: string;
  success: boolean;
  message: string;
  checked_ports: number[];
  open_ports: PortScanPortState[];
  created_at: string;
};

export type PortScanPortState = {
  protocol: string;
  port: number;
  is_open: boolean;
};

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

export type BaselineCheckResult = {
  rule_id: string;
  rule_name: string;
  device_type: string;
  category: string;
  risk_level: string;
  check_type: string;
  check_method: string;
  judge_logic: string;
  remediation: string;
  status: "pass" | "fail" | "unknown" | "not_applicable";
  detail: string;
  evidence: string;
  manual_check_hint: string | null;
};
