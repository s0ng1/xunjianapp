import type {
  Asset,
  BaselineCheckResult,
  BaselineRun,
  LinuxInspection,
  OpenPortEntry,
  PortScanResult,
  SwitchInspection,
} from "@/lib/api";

export type AlertSeverity = "high" | "medium";
export type AlertStatus = "unresolved";
export type DeviceTone = "healthy" | "warning" | "critical" | "unknown";
export type BaselineStatus = "pass" | "fail" | "unknown" | "not_applicable";

export type BaselineEvidenceView = {
  summary: string | null;
  items: string[];
  rawText: string | null;
};

export type AlertItem = {
  id: string;
  assetId: number;
  assetName: string;
  assetIp: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  description: string;
  detectedAt: string;
};

export type BaselineCheckView = {
  key: string;
  title: string;
  status: BaselineStatus;
  severity: string;
  category: string;
  checkType: string;
  summary: string;
  evidence: string;
  evidenceView: BaselineEvidenceView;
  remediation: string;
  manualCheckHint: string | null;
};

export type InspectionSummaryCard = {
  key: string;
  title: string;
  tone: "good" | "medium" | "high" | "neutral";
  summary: string;
  detail: string;
};

export type AssetOverview = {
  asset: Asset;
  latestInspection: LinuxInspection | SwitchInspection | null;
  statusTone: DeviceTone;
  statusLabel: string;
  lastInspectionAt: string | null;
  riskCount: number;
  highRiskCount: number;
  mediumRiskCount: number;
  supportsHistory: boolean;
};

export type AssetDetailView = AssetOverview & {
  alerts: AlertItem[];
  baselineChecks: BaselineCheckView[];
  inspectionSummaryCards: InspectionSummaryCard[];
  openPorts: OpenPortEntry[];
  showOpenPorts: boolean;
  rawOutputs: Array<{ key: string; title: string; content: string }>;
  detailsNote: string | null;
};

export type InspectionListItem = {
  id: string;
  assetId: number | null;
  assetName: string;
  assetIp: string;
  type: "linux" | "switch" | "port_scan" | "baseline";
  status: "success" | "partial" | "failed";
  startedAt: string;
  duration: string;
  summary: string;
  findings: string;
  operator: string;
};

const SHANGHAI_TIMEZONE = "Asia/Shanghai";
const PATCH_EVIDENCE_MAX_VISIBLE_ITEMS = 12;
const PATCH_NO_UPDATES_PATTERNS = [
  "未发现待安装更新",
  "0 upgraded",
  "no packages marked for update",
  "security: 0",
] as const;
const PATCH_INLINE_UPDATE_RE = /\bupdate\s+([a-z0-9][a-z0-9+_.:/@-]*)\s+([0-9][^\s|]*)/gi;
const PATCH_APT_UPGRADE_RE =
  /^([a-z0-9][a-z0-9+_.:/@-]*)\s+([^\s]+)(?:\s+([^\s]+))?\s+\[upgradable from:\s*([^\]]+)\]$/i;
const PATCH_INST_RE = /^inst\s+([^\s]+)\s+\[([^\]]+)\]\s+\(([^ )]+)/i;
const PATCH_YUM_RE = /^([a-z0-9][a-z0-9+_.:/@-]*)\s+([0-9][^\s]*)\s+\S+/i;
const PATCH_ZYPPER_RE =
  /^\S+\s+\|\s+\S+\s+\|\s+([^\s|]+)\s+\|\s+([^\s|]+)\s+\|\s+([^\s|]+)\s+\|\s+[^\s|]+$/i;
const PATCH_FORMATTED_ITEM_RE = /^([a-z0-9][a-z0-9+_.:/@-]*(?: \([^)]+\))?)\s+->\s+([^\s]+)(?:（当前\s+([^)）]+)）)?$/i;

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: SHANGHAI_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function formatAssetType(type: string): string {
  const normalized = type.trim().toLowerCase();
  if (normalized === "linux") {
    return "Linux 服务器";
  }
  if (normalized === "switch") {
    return "交换机";
  }
  return type.toUpperCase();
}

export function formatRiskLevel(level: "critical" | "medium" | "low" | "normal"): string {
  if (level === "critical") {
    return "高危";
  }
  if (level === "medium") {
    return "中危";
  }
  if (level === "low") {
    return "低危";
  }
  return "正常";
}

export function formatAlertStatus(_status: AlertStatus): string {
  return "未处理";
}

export function formatInspectionType(type: InspectionListItem["type"]): string {
  if (type === "linux") {
    return "Linux 巡检";
  }
  if (type === "switch") {
    return "交换机巡检";
  }
  if (type === "port_scan") {
    return "端口扫描";
  }
  return "基线检查";
}

export function formatInspectionStatus(status: InspectionListItem["status"]): string {
  if (status === "success") {
    return "成功";
  }
  if (status === "partial") {
    return "部分异常";
  }
  return "失败";
}

export function buildAssetOverviewList(
  assets: Asset[],
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
): AssetOverview[] {
  const latestLinuxInspectionMap = buildLatestInspectionMap(linuxInspections);
  const latestSwitchInspectionMap = buildLatestInspectionMap(switchInspections);

  return assets.map((asset) => {
    const normalizedType = asset.type.toLowerCase();
    const latestInspection =
      normalizedType === "linux"
        ? latestLinuxInspectionMap.get(`asset:${asset.id}`) ?? latestLinuxInspectionMap.get(`ip:${asset.ip}`) ?? null
        : normalizedType === "switch"
          ? latestSwitchInspectionMap.get(`asset:${asset.id}`) ?? latestSwitchInspectionMap.get(`ip:${asset.ip}`) ?? null
          : null;
    const alerts = latestInspection ? buildAlertsForInspection(asset, latestInspection) : [];
    const highRiskCount = alerts.filter((alert) => alert.severity === "high").length;
    const mediumRiskCount = alerts.filter((alert) => alert.severity === "medium").length;
    const supportsHistory = normalizedType === "linux" || normalizedType === "switch";

    let statusTone: DeviceTone = "unknown";
    let statusLabel = supportsHistory ? "未巡检" : "无历史结果";

    if (latestInspection) {
      if (!latestInspection.success || highRiskCount > 0) {
        statusTone = "critical";
        statusLabel = "高风险";
      } else if (mediumRiskCount > 0) {
        statusTone = "warning";
        statusLabel = "需关注";
      } else {
        statusTone = "healthy";
        statusLabel = "稳定";
      }
    }

    return {
      asset,
      latestInspection,
      statusTone,
      statusLabel,
      lastInspectionAt: latestInspection?.created_at ?? null,
      riskCount: alerts.length,
      highRiskCount,
      mediumRiskCount,
      supportsHistory,
    };
  });
}

export function buildAssetDetailView(
  asset: Asset,
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
): AssetDetailView {
  const overview = buildAssetOverviewList([asset], linuxInspections, switchInspections)[0];

  if (!overview.supportsHistory) {
    return {
      ...overview,
      alerts: [],
      baselineChecks: [],
      inspectionSummaryCards: [],
      openPorts: [],
      showOpenPorts: false,
      rawOutputs: [],
      detailsNote: "当前后端仅提供 Linux 服务器和交换机的巡检结果展示。",
    };
  }

  if (!overview.latestInspection) {
    const deviceLabel = asset.type.toLowerCase() === "switch" ? "交换机" : "Linux";
    return {
      ...overview,
      alerts: [],
      baselineChecks: [],
      inspectionSummaryCards: [],
      openPorts: [],
      showOpenPorts: asset.type.toLowerCase() === "linux",
      rawOutputs: [],
      detailsNote: `该资产还没有 ${deviceLabel} 巡检记录，详情页会在后端产生巡检结果后自动展示。`,
    };
  }

  return {
    ...overview,
    alerts: buildAlertsForInspection(asset, overview.latestInspection),
    baselineChecks: buildBaselineChecks(overview.latestInspection),
    inspectionSummaryCards: buildInspectionSummaryCards(overview.latestInspection),
    openPorts: isLinuxInspection(overview.latestInspection) ? overview.latestInspection.open_ports?.ports ?? [] : [],
    showOpenPorts: isLinuxInspection(overview.latestInspection),
    rawOutputs: buildRawOutputs(overview.latestInspection),
    detailsNote: null,
  };
}

export function buildAlertsList(
  assets: Asset[],
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
): AlertItem[] {
  const latestLinuxInspectionMap = buildLatestInspectionMap(linuxInspections);
  const latestSwitchInspectionMap = buildLatestInspectionMap(switchInspections);

  return assets
    .filter((asset) => {
      const normalizedType = asset.type.toLowerCase();
      return normalizedType === "linux" || normalizedType === "switch";
    })
    .flatMap((asset) => {
      const inspection =
        asset.type.toLowerCase() === "linux"
          ? latestLinuxInspectionMap.get(asset.ip)
          : latestSwitchInspectionMap.get(asset.ip);
      return inspection ? buildAlertsForInspection(asset, inspection) : [];
    })
    .sort((left, right) => {
      if (left.severity !== right.severity) {
        return left.severity === "high" ? -1 : 1;
      }

      return new Date(right.detectedAt).getTime() - new Date(left.detectedAt).getTime();
    });
}

export function buildInspectionHistoryList(
  assets: Asset[],
  linuxInspections: LinuxInspection[],
  switchInspections: SwitchInspection[],
  portScans: PortScanResult[],
  baselineRuns: BaselineRun[],
): InspectionListItem[] {
  const assetById = new Map(assets.map((asset) => [asset.id, asset]));
  const assetByIp = new Map(assets.map((asset) => [asset.ip, asset]));

  const linuxItems: InspectionListItem[] = linuxInspections.map((inspection) => {
    const asset = inspection.asset_id != null ? assetById.get(inspection.asset_id) : assetByIp.get(inspection.ip);
    const failCount = inspection.baseline_results.filter((item) => item.status === "fail").length;

    return {
      id: `linux-${inspection.id}`,
      assetId: asset?.id ?? null,
      assetName: asset?.name ?? inspection.ip,
      assetIp: inspection.ip,
      type: "linux",
      status: !inspection.success ? "failed" : failCount > 0 ? "partial" : "success",
      startedAt: inspection.created_at,
      duration: "--",
      summary: inspection.message,
      findings: `高危/中危失败项 ${failCount} 条，规则总数 ${inspection.baseline_results.length}。`,
      operator: inspection.username,
    };
  });

  const switchItems: InspectionListItem[] = switchInspections.map((inspection) => {
    const asset = inspection.asset_id != null ? assetById.get(inspection.asset_id) : assetByIp.get(inspection.ip);
    const failCount = inspection.baseline_results.filter((item) => item.status === "fail").length;

    return {
      id: `switch-${inspection.id}`,
      assetId: asset?.id ?? null,
      assetName: asset?.name ?? inspection.ip,
      assetIp: inspection.ip,
      type: "switch",
      status: !inspection.success ? "failed" : failCount > 0 ? "partial" : "success",
      startedAt: inspection.created_at,
      duration: "--",
      summary: inspection.message,
      findings: `厂商 ${inspection.vendor}，失败项 ${failCount} 条，规则总数 ${inspection.baseline_results.length}。`,
      operator: inspection.username,
    };
  });

  const portScanItems: InspectionListItem[] = portScans.map((scan) => {
    const asset = scan.asset_id != null ? assetById.get(scan.asset_id) : assetByIp.get(scan.ip);
    const openCount = scan.open_ports.filter((item) => item.is_open).length;

    return {
      id: `port-scan-${scan.id}`,
      assetId: asset?.id ?? null,
      assetName: asset?.name ?? scan.ip,
      assetIp: scan.ip,
      type: "port_scan",
      status: scan.success ? "success" : "failed",
      startedAt: scan.created_at,
      duration: "--",
      summary: scan.message,
      findings: `检查端口 ${scan.checked_ports.join(", ")}，开放端口 ${openCount} 个。`,
      operator: "系统任务",
    };
  });

  const baselineItems: InspectionListItem[] = baselineRuns.map((run) => {
    const asset = run.asset_id != null ? assetById.get(run.asset_id) : assetByIp.get(run.ip);
    const failCount = run.baseline_results.filter((item) => item.status === "fail").length;

    return {
      id: `baseline-${run.source_type}-${run.inspection_id}-${run.created_at}`,
      assetId: asset?.id ?? null,
      assetName: asset?.name ?? run.ip,
      assetIp: run.ip,
      type: "baseline",
      status: !run.success ? "failed" : failCount > 0 ? "partial" : "success",
      startedAt: run.created_at,
      duration: "--",
      summary: run.message,
      findings: `${run.device_type} 基线执行，失败项 ${failCount} 条，规则总数 ${run.baseline_results.length}。`,
      operator: run.username,
    };
  });

  return [...linuxItems, ...switchItems, ...portScanItems, ...baselineItems].sort(
    (left, right) => new Date(right.startedAt).getTime() - new Date(left.startedAt).getTime(),
  );
}

function buildLatestInspectionMap<T extends LinuxInspection | SwitchInspection>(
  inspections: T[],
): Map<string, T> {
  return inspections.reduce((map, inspection) => {
    const key = inspection.asset_id != null ? `asset:${inspection.asset_id}` : `ip:${inspection.ip}`;
    const current = map.get(key);

    if (!current) {
      map.set(key, inspection);
      return map;
    }

    const incomingAt = new Date(inspection.created_at).getTime();
    const currentAt = new Date(current.created_at).getTime();
    if (incomingAt > currentAt) {
      map.set(key, inspection);
    }

    return map;
  }, new Map<string, T>());
}

function buildAlertsForInspection(
  asset: Asset,
  inspection: LinuxInspection | SwitchInspection,
): AlertItem[] {
  const detectedAt = inspection.created_at;
  const alerts: AlertItem[] = [];

  if (!inspection.success) {
    alerts.push({
      id: `${asset.id}-inspection-failed`,
      assetId: asset.id,
      assetName: asset.name,
      assetIp: asset.ip,
      severity: "high",
      status: "unresolved",
      title: "巡检执行失败",
      description: inspection.message,
      detectedAt,
    });
  }

  for (const check of buildBaselineChecks(inspection)) {
    if (check.status !== "fail") {
      continue;
    }

    alerts.push({
      id: `${asset.id}-${check.key}`,
      assetId: asset.id,
      assetName: asset.name,
      assetIp: asset.ip,
      severity: toAlertSeverity(check.severity),
      status: "unresolved",
      title: check.title,
      description: check.summary,
      detectedAt,
    });
  }

  return alerts;
}

function buildBaselineChecks(inspection: LinuxInspection | SwitchInspection): BaselineCheckView[] {
  return inspection.baseline_results.map((check) => ({
    key: check.rule_id,
    title: check.rule_name,
    status: check.status,
    severity: check.risk_level,
    category: check.category,
    checkType: check.check_type,
    summary: buildBaselineSummary(check),
    evidence: check.evidence,
    evidenceView: buildBaselineEvidenceView(check),
    remediation: check.remediation,
    manualCheckHint: check.manual_check_hint,
  }));
}

function buildBaselineEvidenceView(check: BaselineCheckResult): BaselineEvidenceView {
  if (check.rule_id === "linux_patch_update_status") {
    return buildPatchEvidenceView(check.evidence, check.status);
  }

  return {
    summary: null,
    items: [],
    rawText: null,
  };
}

function buildPatchEvidenceView(
  evidence: string,
  status: BaselineCheckResult["status"],
): BaselineEvidenceView {
  const text = evidence.trim();
  if (!text) {
    return {
      summary: null,
      items: [],
      rawText: null,
    };
  }

  const lowered = text.toLowerCase();
  if (PATCH_NO_UPDATES_PATTERNS.some((pattern) => lowered.includes(pattern.toLowerCase()))) {
    return {
      summary: "未发现待安装更新",
      items: [],
      rawText: null,
    };
  }

  const items = collectPatchEvidenceItems(text);
  if (items.length === 0) {
    return {
      summary: null,
      items: [],
      rawText: null,
    };
  }

  const visibleItems = items.slice(0, PATCH_EVIDENCE_MAX_VISIBLE_ITEMS);
  const hiddenCount = items.length - visibleItems.length;
  const summary =
    status === "unknown"
      ? hiddenCount > 0
        ? `识别到 ${items.length} 条更新线索，仅展示前 ${visibleItems.length} 条，需人工确认是否属于安全补丁。`
        : `识别到 ${items.length} 条更新线索，需人工确认是否属于安全补丁。`
      : hiddenCount > 0
        ? `识别到 ${items.length} 个待更新包，仅展示前 ${visibleItems.length} 个。`
        : `识别到 ${items.length} 个待更新包。`;

  return {
    summary,
    items: visibleItems,
    rawText: shouldShowPatchRawText(text, items) ? text : null,
  };
}

function collectPatchEvidenceItems(text: string): string[] {
  const seen = new Set<string>();
  const items: string[] = [];

  for (const segment of splitPatchEvidenceSegments(text)) {
    const parsed = parsePatchEvidenceSegment(segment);
    if (!parsed || seen.has(parsed)) {
      continue;
    }

    seen.add(parsed);
    items.push(parsed);
  }

  for (const match of text.matchAll(PATCH_INLINE_UPDATE_RE)) {
    const name = match[1]?.trim();
    const version = match[2]?.trim();
    if (!name || !version) {
      continue;
    }

    const item = `${name} -> ${version}`;
    if (seen.has(item)) {
      continue;
    }

    seen.add(item);
    items.push(item);
  }

  return items;
}

function splitPatchEvidenceSegments(text: string): string[] {
  return text
    .split(/\n+/)
    .flatMap((segment) => {
      const cleaned = segment.trim();
      if (!cleaned) {
        return [];
      }
      if (PATCH_ZYPPER_RE.test(cleaned)) {
        return [cleaned];
      }
      return cleaned.split(/\s+\|\s+/);
    })
    .map((segment) => segment.trim())
    .filter(Boolean);
}

function parsePatchEvidenceSegment(segment: string): string | null {
  const cleaned = segment.replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return null;
  }

  const lowered = cleaned.toLowerCase();
  if (
    lowered.startsWith("listing") ||
    /\beta\b/i.test(cleaned) ||
    /\bb\/s\b/i.test(cleaned) ||
    lowered.startsWith("[")
  ) {
    return null;
  }

  const formattedMatch = cleaned.match(PATCH_FORMATTED_ITEM_RE);
  if (formattedMatch) {
    const [, name, version, fromVersion] = formattedMatch;
    return fromVersion ? `${name} -> ${version}（当前 ${fromVersion}）` : `${name} -> ${version}`;
  }

  const aptMatch = cleaned.match(PATCH_APT_UPGRADE_RE);
  if (aptMatch) {
    const [, name, version, arch, fromVersion] = aptMatch;
    const label = arch && /^[a-z0-9]+$/i.test(arch) ? `${name} (${arch})` : name;
    return `${label} -> ${version}（当前 ${fromVersion}）`;
  }

  const instMatch = cleaned.match(PATCH_INST_RE);
  if (instMatch) {
    const [, name, fromVersion, version] = instMatch;
    return `${name} -> ${version}（当前 ${fromVersion}）`;
  }

  const zypperMatch = cleaned.match(PATCH_ZYPPER_RE);
  if (zypperMatch) {
    const [, name, currentVersion, availableVersion] = zypperMatch;
    return `${name} -> ${availableVersion}（当前 ${currentVersion}）`;
  }

  const yumMatch = cleaned.match(PATCH_YUM_RE);
  if (yumMatch) {
    const [, name, version] = yumMatch;
    return `${name} -> ${version}`;
  }

  return null;
}

function shouldShowPatchRawText(text: string, items: string[]): boolean {
  if (items.length === 0) {
    return false;
  }

  return text.length > 220 || /\bETA\b|\bB\/s\b|\[[=\s-]+\]/i.test(text);
}

function buildInspectionSummaryCards(
  inspection: LinuxInspection | SwitchInspection,
): InspectionSummaryCard[] {
  if (!isLinuxInspection(inspection)) {
    return [];
  }

  const cards: InspectionSummaryCard[] = [];
  const timeSyncCheck = findBaselineResult(inspection.baseline_results, "linux_time_sync_enabled");
  const auditdCheck = findBaselineResult(inspection.baseline_results, "linux_auditd_enabled");

  if (inspection.time_sync_status || timeSyncCheck) {
    cards.push({
      key: "time-sync",
      title: "时间同步状态",
      tone: mapSummaryTone(timeSyncCheck),
      summary:
        inspection.time_sync_status?.service_status != null
          ? `服务状态：${inspection.time_sync_status.service_status}`
          : "未返回独立服务状态。",
      detail: timeSyncCheck?.detail ?? "后端未返回时间同步基线结论。",
    });
  }

  if (inspection.auditd_status || auditdCheck) {
    const auditctlText =
      inspection.auditd_status?.auditctl_status != null
        ? ` auditctl=${inspection.auditd_status.auditctl_status}`
        : "";
    cards.push({
      key: "auditd",
      title: "审计服务状态",
      tone: mapSummaryTone(auditdCheck),
      summary:
        inspection.auditd_status?.service_status != null
          ? `auditd 服务：${inspection.auditd_status.service_status}`
          : "未返回 auditd 服务状态。",
      detail: `${auditdCheck?.detail ?? "后端未返回审计基线结论。"}${auditctlText}`.trim(),
    });
  }

  return cards;
}

function buildRawOutputs(
  inspection: LinuxInspection | SwitchInspection,
): Array<{ key: string; title: string; content: string }> {
  if (isLinuxInspection(inspection)) {
    return [
      {
        key: "open-ports",
        title: "开放端口原始输出",
        content: inspection.open_ports?.raw_output ?? "",
      },
      {
        key: "ssh-config",
        title: "SSH 配置原始输出",
        content: inspection.ssh_config?.raw_output ?? "",
      },
      {
        key: "firewall",
        title: "防火墙原始输出",
        content: inspection.firewall_status?.raw_output ?? "",
      },
      {
        key: "time-sync",
        title: "时间同步原始输出",
        content: inspection.time_sync_status?.raw_output ?? "",
      },
      {
        key: "auditd",
        title: "审计服务原始输出",
        content: inspection.auditd_status?.raw_output ?? "",
      },
    ].filter((item) => item.content.trim().length > 0);
  }

  return [
    {
      key: "switch-config",
      title: `${inspection.vendor} 配置原文`,
      content: inspection.raw_config ?? "",
    },
  ].filter((item) => item.content.trim().length > 0);
}

function isLinuxInspection(inspection: LinuxInspection | SwitchInspection): inspection is LinuxInspection {
  return "open_ports" in inspection;
}

function buildBaselineSummary(check: BaselineCheckResult): string {
  const riskLevel = check.risk_level.trim().toLowerCase();
  const riskLabel = riskLevel === "high" ? "高危" : riskLevel === "medium" ? "中危" : "低危";
  return `${riskLabel}，当前结论：${check.detail}`;
}

function toAlertSeverity(riskLevel: string): AlertSeverity {
  return riskLevel.trim().toLowerCase() === "high" ? "high" : "medium";
}

function mapSummaryTone(check: BaselineCheckResult | undefined): InspectionSummaryCard["tone"] {
  if (!check || check.status === "unknown") {
    return "neutral";
  }
  if (check.status === "pass") {
    return "good";
  }
  return toAlertSeverity(check.risk_level) === "high" ? "high" : "medium";
}

function findBaselineResult(
  results: BaselineCheckResult[],
  ruleId: string,
): BaselineCheckResult | undefined {
  return results.find((item) => item.rule_id === ruleId);
}
