export type HealthResponse = {
  status: string;
  service: string;
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

export type SSHTestPayload = {
  ip: string;
  username: string;
  password: string;
};

export type SSHTestResult = {
  success: boolean;
  message: string;
};

export type OpenPortEntry = {
  protocol: string;
  local_address: string;
  port: string;
  state: string | null;
};

export type OpenPortsResult = {
  ports: OpenPortEntry[];
  raw_output: string;
};

export type SSHConfigResult = {
  settings: Record<string, string>;
  raw_output: string;
};

export type FirewallStatusResult = {
  firewalld: string | null;
  ufw: string | null;
  iptables_rules: string[];
  raw_output: string;
};

export type TimeSyncStatusResult = {
  timedatectl: string | null;
  service_status: string | null;
  raw_output: string;
};

export type AuditdStatusResult = {
  service_status: string | null;
  auditctl_status: string | null;
  raw_output: string;
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

export type LinuxInspection = {
  id: number;
  asset_id: number | null;
  ip: string;
  username: string;
  success: boolean;
  message: string;
  open_ports: OpenPortsResult | null;
  ssh_config: SSHConfigResult | null;
  firewall_status: FirewallStatusResult | null;
  time_sync_status: TimeSyncStatusResult | null;
  auditd_status: AuditdStatusResult | null;
  baseline_results: BaselineCheckResult[];
  created_at: string;
};

export type SwitchInspection = {
  id: number;
  asset_id: number | null;
  ip: string;
  username: string;
  success: boolean;
  vendor: string;
  message: string;
  raw_config: string | null;
  baseline_results: BaselineCheckResult[];
  created_at: string;
};

export type PortScanPayload = {
  ip: string;
  ports: number[];
};

export type PortScanPortState = {
  protocol: string;
  port: number;
  is_open: boolean;
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

export type LinuxInspectionPayload = SSHTestPayload;

export type SwitchInspectionPayload = SSHTestPayload & {
  vendor: string;
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

export type DailyFocusItem = {
  id: string;
  asset_id: number | null;
  asset_name: string;
  asset_ip: string;
  section: "today_must_handle" | "today_changes" | "weekly_plan";
  priority_rank: number;
  severity: string;
  headline: string;
  summary: string;
  detected_at: string;
  source_type: string;
  rule_id: string | null;
  persistent_days: number;
  status: DailyFocusItemStatus;
  remark: string | null;
  updated_at: string | null;
  updated_by: string | null;
};

export type DailyFocusAssetGroup = {
  asset_id: number | null;
  asset_name: string;
  asset_ip: string;
  items: DailyFocusItem[];
};

export type DailyFocusItemStatus =
  | "pending"
  | "in_progress"
  | "resolved"
  | "ignored"
  | "needs_manual_confirmation";

export type DailyFocusPriorityDevice = {
  asset_id: number | null;
  asset_name: string;
  asset_ip: string;
  high_count: number;
  medium_count: number;
  today_changes_count: number;
  needs_manual_confirmation_count: number;
};

export type DailyFocusItemState = {
  item_id: string;
  reference_date: string;
  status: DailyFocusItemStatus;
  remark: string | null;
  updated_at: string;
  updated_by: string;
};

export type DailyFocusItemStateUpdatePayload = {
  reference_date: string;
  status: DailyFocusItemStatus;
  remark?: string;
  updated_by?: string;
};

export type DailyFocus = {
  reference_date: string;
  generated_at: string;
  today_summary: string;
  summary: {
    must_handle_count: number;
    today_changes_count: number;
    weekly_plan_count: number;
  };
  priority_devices: DailyFocusPriorityDevice[];
  today_must_handle: DailyFocusAssetGroup[];
  today_changes: DailyFocusItem[];
  weekly_plan: DailyFocusItem[];
};

export type AssetPortScanPayload = {
  ports: number[];
};

const PUBLIC_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const INTERNAL_API_BASE_URL =
  process.env.INTERNAL_API_BASE_URL ?? PUBLIC_API_BASE_URL;

const API_BASE_URL =
  typeof window === "undefined" ? INTERNAL_API_BASE_URL : PUBLIC_API_BASE_URL;

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
};

async function fetchFromApi<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = options.body === undefined ? undefined : { "Content-Type": "application/json" };
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      if (payload.error?.message) {
        detail = payload.error.message;
      }
    } catch {
      // Ignore non-JSON error bodies and keep the HTTP status message.
    }
    throw new Error(`API request failed: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function fetchBackendHealth(): Promise<HealthResponse> {
  return fetchFromApi<HealthResponse>("/health");
}

export async function fetchAssets(): Promise<Asset[]> {
  return fetchFromApi<Asset[]>("/api/v1/assets");
}

export async function createAsset(payload: AssetCreatePayload): Promise<Asset> {
  return fetchFromApi<Asset>("/api/v1/assets", { method: "POST", body: payload });
}

export async function updateAsset(assetId: number, payload: AssetUpdatePayload): Promise<Asset> {
  return fetchFromApi<Asset>(`/api/v1/assets/${assetId}`, { method: "PATCH", body: payload });
}

export async function deleteAsset(assetId: number): Promise<void> {
  await fetchFromApi<void>(`/api/v1/assets/${assetId}`, { method: "DELETE" });
}

export async function runSshTest(payload: SSHTestPayload): Promise<SSHTestResult> {
  return fetchFromApi<SSHTestResult>("/api/v1/ssh/test", { method: "POST", body: payload });
}

export async function runAssetSshTest(assetId: number): Promise<SSHTestResult> {
  return fetchFromApi<SSHTestResult>(`/api/v1/assets/${assetId}/ssh-test`, { method: "POST" });
}

export async function fetchPortScans(): Promise<PortScanResult[]> {
  return fetchFromApi<PortScanResult[]>("/api/v1/port-scans");
}

export async function runPortScan(payload: PortScanPayload): Promise<PortScanResult> {
  return fetchFromApi<PortScanResult>("/api/v1/port-scans/run", { method: "POST", body: payload });
}

export async function runAssetPortScan(
  assetId: number,
  payload: AssetPortScanPayload,
): Promise<PortScanResult> {
  return fetchFromApi<PortScanResult>(`/api/v1/assets/${assetId}/port-scan`, {
    method: "POST",
    body: payload,
  });
}

export async function fetchLinuxInspections(): Promise<LinuxInspection[]> {
  return fetchFromApi<LinuxInspection[]>("/api/v1/linux-inspections");
}

export async function runLinuxInspection(payload: LinuxInspectionPayload): Promise<LinuxInspection> {
  return fetchFromApi<LinuxInspection>("/api/v1/linux-inspections/run", { method: "POST", body: payload });
}

export async function runAssetInspection(assetId: number): Promise<BaselineRun> {
  return fetchFromApi<BaselineRun>(`/api/v1/assets/${assetId}/inspect`, { method: "POST" });
}

export async function fetchSwitchInspections(): Promise<SwitchInspection[]> {
  return fetchFromApi<SwitchInspection[]>("/api/v1/switch-inspections");
}

export async function runSwitchInspection(payload: SwitchInspectionPayload): Promise<SwitchInspection> {
  return fetchFromApi<SwitchInspection>("/api/v1/switch-inspections/run", { method: "POST", body: payload });
}

export async function fetchBaselineRuns(): Promise<BaselineRun[]> {
  return fetchFromApi<BaselineRun[]>("/api/v1/baseline-checks");
}

export async function fetchDailyFocus(referenceDate?: string): Promise<DailyFocus> {
  const query = referenceDate ? `?reference_date=${encodeURIComponent(referenceDate)}` : "";
  return fetchFromApi<DailyFocus>(`/api/v1/daily-focus${query}`);
}

export async function updateDailyFocusItemState(
  itemId: string,
  payload: DailyFocusItemStateUpdatePayload,
): Promise<DailyFocusItemState> {
  return fetchFromApi<DailyFocusItemState>(`/api/v1/daily-focus/items/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function runLinuxBaseline(payload: LinuxInspectionPayload): Promise<BaselineRun> {
  return fetchFromApi<BaselineRun>("/api/v1/baseline-checks/linux/run", { method: "POST", body: payload });
}

export async function runAssetBaseline(assetId: number): Promise<BaselineRun> {
  return fetchFromApi<BaselineRun>(`/api/v1/assets/${assetId}/baseline`, { method: "POST" });
}

export async function runSwitchBaseline(payload: SwitchInspectionPayload): Promise<BaselineRun> {
  return fetchFromApi<BaselineRun>("/api/v1/baseline-checks/switch/run", { method: "POST", body: payload });
}

export async function rerunLinuxBaseline(inspectionId: number): Promise<BaselineRun> {
  return fetchFromApi<BaselineRun>(`/api/v1/baseline-checks/linux/${inspectionId}/rerun`, { method: "POST" });
}

export async function rerunSwitchBaseline(inspectionId: number): Promise<BaselineRun> {
  return fetchFromApi<BaselineRun>(`/api/v1/baseline-checks/switch/${inspectionId}/rerun`, { method: "POST" });
}

export async function fetchResultDataset(): Promise<{
  assets: Asset[];
  linuxInspections: LinuxInspection[];
  switchInspections: SwitchInspection[];
}> {
  const [assets, linuxInspections, switchInspections] = await Promise.all([
    fetchAssets(),
    fetchLinuxInspections(),
    fetchSwitchInspections(),
  ]);

  return { assets, linuxInspections, switchInspections };
}

export { API_BASE_URL };
