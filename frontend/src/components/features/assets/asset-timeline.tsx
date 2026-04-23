import { StatePanel } from "@/components/state-panel";
import type { Asset } from "@/lib/api";
import type { AssetDetailView } from "@/lib/inspection-view";
import { formatAssetType, formatDateTime } from "@/lib/inspection-view";

type AssetTimelineProps = {
  asset: Asset;
  detail: AssetDetailView;
};

type TimelineItem = {
  key: string;
  title: string;
  description: string;
  timestamp: string | null;
  tone: "good" | "medium" | "high" | "neutral";
  meta: string[];
};

export function AssetTimeline({ asset, detail }: AssetTimelineProps) {
  const timelineItems = buildTimelineItems(asset, detail);

  if (detail.detailsNote) {
    return (
      <section className="section-card asset-timeline-card">
        <TimelineHeader count={timelineItems.length} />
        <div className="asset-timeline">
          <TimelineList items={timelineItems} />
        </div>
        <StatePanel
          tone="info"
          title="当前资产暂无可展示详情"
          description={detail.detailsNote}
          action={detail.supportsHistory ? undefined : { href: "/assets", label: "返回资产列表" }}
        />
      </section>
    );
  }

  return (
    <section className="section-card asset-timeline-card">
      <TimelineHeader count={timelineItems.length} />
      <div className="asset-timeline">
        <TimelineList items={timelineItems} />
      </div>

      {detail.rawOutputs.length > 0 ? (
        <div className="asset-raw-output-panel">
          <div className="section-header compact">
            <div>
              <h3 className="section-title">原始输出</h3>
              <p className="section-description">后端返回的最近一次巡检原始文本，默认折叠。</p>
            </div>
          </div>

          <div className="detail-stack">
            {detail.rawOutputs.map((output) => (
              <details key={output.key} className="fold-card">
                <summary>{output.title}</summary>
                <pre className="mono">{output.content}</pre>
              </details>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function TimelineHeader({ count }: { count: number }) {
  return (
    <div className="section-header">
      <div>
        <h3 className="section-title">操作时间线</h3>
        <p className="section-description">统一展示资产纳管、巡检、风险、基线与端口暴露状态。</p>
      </div>
      <span className="status-chip tone-neutral">{count} 个节点</span>
    </div>
  );
}

function TimelineList({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="asset-timeline-list">
      {items.map((item) => (
        <li key={item.key} className={`asset-timeline-item tone-${item.tone}`}>
          <div className="asset-timeline-node" aria-hidden="true" />
          <article className="asset-timeline-content">
            <div className="asset-timeline-topline">
              <div>
                <h4>{item.title}</h4>
                <p>{item.description}</p>
              </div>
              <time>{formatDateTime(item.timestamp)}</time>
            </div>
            <div className="asset-timeline-meta">
              {item.meta.map((meta) => (
                <span key={meta} className={`status-chip tone-${item.tone}`}>
                  {meta}
                </span>
              ))}
            </div>
          </article>
        </li>
      ))}
    </ol>
  );
}

function buildTimelineItems(asset: Asset, detail: AssetDetailView): TimelineItem[] {
  const items: TimelineItem[] = [
    {
      key: "asset-created",
      title: "资产纳管",
      description: `${asset.name} 已纳入资产台账，连接方式为 ${asset.connection_type.toUpperCase()} / ${asset.port}。`,
      timestamp: asset.created_at,
      tone: asset.is_enabled ? "good" : "neutral",
      meta: [
        formatAssetType(asset.type),
        asset.credential_configured ? "凭据已配置" : "凭据未配置",
        asset.is_enabled ? "已启用" : "已停用",
      ],
    },
  ];

  if (!detail.latestInspection) {
    items.push({
      key: "inspection-empty",
      title: "等待首次巡检",
      description: detail.detailsNote ?? "当前还没有匹配到该资产的巡检记录。",
      timestamp: null,
      tone: "neutral",
      meta: ["无历史结果"],
    });
    return items;
  }

  const failedChecks = detail.baselineChecks.filter((check) => check.status === "fail");
  const passedChecks = detail.baselineChecks.filter((check) => check.status === "pass");
  const inspectionTone = !detail.latestInspection.success
    ? "high"
    : failedChecks.length > 0
      ? "medium"
      : "good";

  items.push({
    key: "latest-inspection",
    title: `${formatAssetType(asset.type)}巡检`,
    description: detail.latestInspection.message,
    timestamp: detail.latestInspection.created_at,
    tone: inspectionTone,
    meta: [
      detail.latestInspection.success ? "执行成功" : "执行失败",
      `操作账号 ${detail.latestInspection.username}`,
      detail.statusLabel,
    ],
  });

  items.push({
    key: "risk-summary",
    title: "风险判定",
    description:
      detail.alerts.length > 0
        ? `发现 ${detail.highRiskCount} 个高危、${detail.mediumRiskCount} 个中危风险，当前均视为未处理。`
        : "最近一次巡检未派生未处理风险项。",
    timestamp: detail.lastInspectionAt,
    tone: detail.highRiskCount > 0 ? "high" : detail.mediumRiskCount > 0 ? "medium" : "good",
    meta: [`风险 ${detail.riskCount}`, `高危 ${detail.highRiskCount}`, `中危 ${detail.mediumRiskCount}`],
  });

  if (detail.baselineChecks.length > 0) {
    items.push({
      key: "baseline-summary",
      title: "基线检查",
      description: `共返回 ${detail.baselineChecks.length} 条基线结果，失败项 ${failedChecks.length} 条。`,
      timestamp: detail.lastInspectionAt,
      tone: failedChecks.length > 0 ? "high" : "good",
      meta: [`通过 ${passedChecks.length}`, `失败 ${failedChecks.length}`, `总数 ${detail.baselineChecks.length}`],
    });
  }

  if (detail.showOpenPorts) {
    items.push({
      key: "open-ports",
      title: "端口暴露面",
      description:
        detail.openPorts.length > 0
          ? `最近一次 Linux 巡检返回 ${detail.openPorts.length} 个监听端口。`
          : "最近一次 Linux 巡检没有返回开放端口明细。",
      timestamp: detail.lastInspectionAt,
      tone: detail.openPorts.length > 0 ? "medium" : "neutral",
      meta:
        detail.openPorts.length > 0
          ? detail.openPorts.slice(0, 4).map((port) => `${port.protocol}/${port.port}`)
          : ["无端口数据"],
    });
  }

  if (detail.inspectionSummaryCards.length > 0) {
    items.push({
      key: "status-summary",
      title: "补充状态",
      description: "时间同步、审计服务等补充状态已随巡检结果归档。",
      timestamp: detail.lastInspectionAt,
      tone: detail.inspectionSummaryCards.some((card) => card.tone === "high")
        ? "high"
        : detail.inspectionSummaryCards.some((card) => card.tone === "medium")
          ? "medium"
          : "good",
      meta: detail.inspectionSummaryCards.map((card) => `${card.title}: ${card.summary}`),
    });
  }

  return items;
}
