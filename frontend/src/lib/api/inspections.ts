import { fetchFromApi } from "./client";

// Shared payload types
export type SSHTestPayload = {
  ip: string;
  username: string;
  password: string;
};

export type LinuxInspectionPayload = SSHTestPayload;

export type SwitchInspectionPayload = SSHTestPayload & {
  vendor: string;
};

// Inspection result types
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

export type PortScanResult = {
  id: number;
  asset_id: number | null;
  ip: string;
  success: boolean;
  message: string;
  checked_ports: number[];
  open_ports: Array<{ protocol: string; port: number; is_open: boolean }>;
  created_at: string;
};

export const inspectionsApi = {
  // Linux inspections
  listLinux: () => fetchFromApi<LinuxInspection[]>("/api/v1/linux-inspections"),

  runLinux: (payload: LinuxInspectionPayload) =>
    fetchFromApi<LinuxInspection>("/api/v1/linux-inspections/run", { method: "POST", body: payload }),

  // Switch inspections
  listSwitch: () => fetchFromApi<SwitchInspection[]>("/api/v1/switch-inspections"),

  runSwitch: (payload: SwitchInspectionPayload) =>
    fetchFromApi<SwitchInspection>("/api/v1/switch-inspections/run", { method: "POST", body: payload }),

  // Port scans
  listPortScans: () => fetchFromApi<PortScanResult[]>("/api/v1/port-scans"),

  runPortScan: (payload: { ip: string; ports: number[] }) =>
    fetchFromApi<PortScanResult>("/api/v1/port-scans/run", { method: "POST", body: payload }),
};
