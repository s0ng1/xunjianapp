import type { ReactNode } from "react";

import { StatePanel } from "@/components/state-panel";
import { MetricCard, type MetricCardTone } from "@/components/ui/metric-card";
import { SeverityBadge } from "@/components/ui/severity-badge";
import type { Asset, BaselineRun } from "@/lib/api";

export type OperationStageHeaderProps = {
  groupLabel: string;
  operationLabel: string;
  description: string;
};

export function OperationStageHeader({
  groupLabel,
  operationLabel,
  description,
}: OperationStageHeaderProps) {
  return (
    <div className="operation-stage-head">
      <div>
        <span className="operation-stage-kicker">{groupLabel}</span>
        <h3>{operationLabel}</h3>
      </div>
      <span className="section-meta">{description}</span>
    </div>
  );
}

export function EmptyAssetStage({ stageHeader }: { stageHeader: ReactNode }) {
  return (
    <section className="operation-stage-card">
      {stageHeader}
      <StatePanel tone="info" title="还没有可执行资产" description="先录入资产并配置连接信息，再从这里直接发起动作。" />
    </section>
  );
}

export function AssetSelector({
  assets,
  selectedAssetId,
  onSelectedAssetChange,
}: {
  assets: Asset[];
  selectedAssetId: number | null;
  onSelectedAssetChange: (assetId: number | null) => void;
}) {
  return (
    <div className="form-grid">
      <label className="field-stack field-span-2">
        <span className="field-label">当前资产</span>
        <select
          className="control-select"
          value={selectedAssetId ?? ""}
          onChange={(event) => onSelectedAssetChange(event.target.value ? Number(event.target.value) : null)}
        >
          <option value="">请选择资产</option>
          {assets.map((asset) => (
            <option key={asset.id} value={asset.id}>
              {asset.name} / {asset.ip} / {asset.type.toUpperCase()}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export function SelectedAssetSummary({ asset }: { asset: Asset | null }) {
  if (asset == null) {
    return null;
  }

  return (
    <MetricCard label="当前执行对象" value={asset.name} valueClassName="metric-value metric-value-compact">
      <p className="metric-hint">
        {asset.ip} / {asset.type.toUpperCase()} / {asset.connection_type.toUpperCase()}:{asset.port}
      </p>
      <p className="metric-hint">
        {asset.is_enabled ? "已启用" : "已停用"} / {asset.username ?? "无用户名"} /{" "}
        {asset.credential_configured ? "凭据已配置" : "凭据缺失"}
      </p>
    </MetricCard>
  );
}

export function ResultCard({
  title,
  summary,
  detail,
  tone,
}: {
  title: string;
  summary: string;
  detail?: string;
  tone: MetricCardTone;
}) {
  return (
    <MetricCard label={title} value={summary} tone={tone} valueClassName="metric-value metric-value-large">
      {detail ? <p className="metric-hint">{detail}</p> : null}
    </MetricCard>
  );
}

export function InspectionCard({
  title,
  success,
  message,
  baselineResults,
  vendor,
}: {
  title: string;
  success: boolean;
  message: string;
  baselineResults: BaselineRun["baseline_results"];
  vendor?: string;
}) {
  const failCount = baselineResults.filter((item) => item.status === "fail").length;
  const unknownCount = baselineResults.filter((item) => item.status === "unknown").length;
  const notApplicableCount = baselineResults.filter((item) => item.status === "not_applicable").length;

  return (
    <div className="result-stack">
      <ResultCard
        title={vendor ? `${title} / ${vendor}` : title}
        tone={success ? (failCount > 0 ? "medium" : "good") : "high"}
        summary={message}
        detail={`失败项 ${failCount}，待补核 ${unknownCount}，不适用 ${notApplicableCount}，总规则 ${baselineResults.length}`}
      />
      {baselineResults.length > 0 ? (
        <div className="list-stack">
          {baselineResults.slice(0, 3).map((item) => (
            <article key={item.rule_id} className="list-item">
              <div className="list-item-main">
                <h4 className="list-item-title">{item.rule_name}</h4>
                <p className="list-item-copy">{item.detail}</p>
                <p className="list-item-copy">{item.evidence}</p>
              </div>
              <div className="list-item-meta">
                <SeverityBadge
                  className="status-chip"
                  tone={item.status === "fail" ? "high" : item.status === "pass" ? "good" : "neutral"}
                >
                  {item.status}
                </SeverityBadge>
                <SeverityBadge className="status-chip" tone="neutral">
                  {item.risk_level}
                </SeverityBadge>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
}
