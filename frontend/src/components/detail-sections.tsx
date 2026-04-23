import { StatePanel } from "@/components/state-panel";
import type { AssetDetailView, BaselineCheckView } from "@/lib/inspection-view";
import { formatDateTime } from "@/lib/inspection-view";

type DetailSectionsProps = {
  detail: AssetDetailView;
};

const CHECK_STATUS_LABEL: Record<string, string> = {
  pass: "通过",
  fail: "不合规",
  unknown: "待补核",
  not_applicable: "不适用",
};

export function DetailSections({ detail }: DetailSectionsProps) {
  if (detail.detailsNote) {
    return (
      <StatePanel
        tone="info"
        title="当前资产暂无可展示详情"
        description={detail.detailsNote}
        action={detail.supportsHistory ? undefined : { href: "/assets", label: "返回资产列表" }}
      />
    );
  }

  return (
    <>
      <section className="section-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">当前风险</h3>
            <p className="section-description">
              基于最新一次巡检结果中的后端基线失败项生成，当前所有条目均视为未处理。
            </p>
          </div>
        </div>

        {detail.alerts.length > 0 ? (
          <div className="list-stack">
            {detail.alerts.map((alert) => (
              <article key={alert.id} className="list-item">
                <div className="list-item-main">
                  <h4 className="list-item-title">{alert.title}</h4>
                  <p className="list-item-copy">{alert.description}</p>
                </div>
                <div className="list-item-meta">
                  <span className={`status-chip tone-${alert.severity}`}>
                    {alert.severity === "high" ? "高危" : "中危"}
                  </span>
                  <span className="status-chip tone-neutral">未处理</span>
                  <span className="status-chip tone-neutral">{formatDateTime(alert.detectedAt)}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <StatePanel
            tone="empty"
            title="当前没有派生风险项"
            description="这台设备的最新巡检结果没有返回失败的后端基线项。"
          />
        )}
      </section>

      <section className="section-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">基线检查结果</h3>
            <p className="section-description">
              直接展示后端返回的结论、证据和整改建议，不再把原始命令输出作为主展示区域。
            </p>
          </div>
        </div>

        {detail.baselineChecks.length > 0 ? (
          <div className="baseline-grid">
            {detail.baselineChecks.map((check) => (
              <article key={check.key} className={`check-card tone-${mapCheckTone(check.status)}`}>
                <div className="check-topline">
                  <h4 className="check-title">{check.title}</h4>
                  <span className={`status-chip tone-${mapCheckTone(check.status)}`}>
                    {CHECK_STATUS_LABEL[check.status]}
                  </span>
                </div>
                <div className="check-meta-row">
                  <span className="status-chip tone-neutral">{formatCategory(check.category)}</span>
                  <span className="status-chip tone-neutral">{formatCheckType(check.checkType)}</span>
                  <span className={`status-chip tone-${mapSeverityTone(check.severity)}`}>
                    {formatSeverity(check.severity)}
                  </span>
                </div>
                <p className="check-summary">{check.summary}</p>
                <div className="check-copy-grid">
                  <CheckEvidence check={check} />
                  <p className="check-detail">
                    <strong>整改建议：</strong>
                    {check.remediation}
                  </p>
                  {check.manualCheckHint ? (
                    <p className="check-detail">
                      <strong>人工核查提示：</strong>
                      {check.manualCheckHint}
                    </p>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <StatePanel
            tone="empty"
            title="没有基线结果"
            description="当前巡检结果没有返回可展示的基线明细。"
          />
        )}
      </section>

      {detail.inspectionSummaryCards.length > 0 ? (
        <section className="section-card">
          <div className="section-header">
            <div>
              <h3 className="section-title">补充状态</h3>
              <p className="section-description">
                展示时间同步和审计服务等补充状态，便于快速复核后端采集结果。
              </p>
            </div>
          </div>

          <div className="detail-grid">
            {detail.inspectionSummaryCards.map((card) => (
              <article key={card.key} className="metric-card">
                <div className="metric-label">{card.title}</div>
                <div className={`status-chip tone-${card.tone}`}>{card.summary}</div>
                <p className="metric-hint">{card.detail}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {detail.showOpenPorts ? (
        <section className="section-card">
          <div className="section-header">
            <div>
              <h3 className="section-title">开放端口</h3>
              <p className="section-description">
                展示最近一次巡检返回的监听端口，便于快速确认服务暴露面。
              </p>
            </div>
          </div>

          {detail.openPorts.length > 0 ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>协议</th>
                    <th>地址</th>
                    <th>端口</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.openPorts.map((port, index) => (
                    <tr key={`${port.protocol}-${port.local_address}-${port.port}-${index}`}>
                      <td>{port.protocol}</td>
                      <td className="mono">{port.local_address}</td>
                      <td className="mono">{port.port}</td>
                      <td>{port.state ?? "--"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <StatePanel
              tone="empty"
              title="没有可展示的端口数据"
              description="当前巡检结果没有返回开放端口明细，可能是巡检失败或目标未返回数据。"
            />
          )}
        </section>
      ) : null}
    </>
  );
}

function mapCheckTone(status: string): "good" | "medium" | "high" | "neutral" {
  if (status === "pass") {
    return "good";
  }
  if (status === "fail") {
    return "high";
  }
  return "neutral";
}

function mapSeverityTone(severity: string): "good" | "medium" | "high" | "neutral" {
  const normalized = severity.trim().toLowerCase();
  if (normalized === "high") {
    return "high";
  }
  if (normalized === "medium") {
    return "medium";
  }
  if (normalized === "low") {
    return "good";
  }
  return "neutral";
}

function formatSeverity(severity: string): string {
  const normalized = severity.trim().toLowerCase();
  if (normalized === "high") {
    return "高危";
  }
  if (normalized === "medium") {
    return "中危";
  }
  if (normalized === "low") {
    return "低危";
  }
  return severity || "--";
}

function formatCategory(category: string): string {
  const normalized = category.trim().toLowerCase();
  if (normalized === "identity_authentication") {
    return "身份鉴别";
  }
  if (normalized === "security_audit") {
    return "安全审计";
  }
  if (normalized === "access_control") {
    return "访问控制";
  }
  if (normalized === "security_protection") {
    return "安全保护";
  }
  if (normalized === "malware_protection") {
    return "恶意代码防范";
  }
  return category || "--";
}

function formatCheckType(checkType: string): string {
  const normalized = checkType.trim().toLowerCase();
  if (normalized === "auto") {
    return "自动检查";
  }
  if (normalized === "semi-auto") {
    return "半自动";
  }
  if (normalized === "manual") {
    return "人工确认";
  }
  if (normalized === "not_applicable") {
    return "不适用";
  }
  return checkType || "--";
}

function CheckEvidence({ check }: { check: BaselineCheckView }) {
  if (check.evidenceView.items.length > 0) {
    return (
      <div className="check-detail-block">
        <p className="check-detail">
          <strong>核查证据：</strong>
          {check.evidenceView.summary ?? "已识别到待确认更新项。"}
        </p>
        <ul className="check-evidence-list">
          {check.evidenceView.items.map((item, index) => (
            <li key={`${check.key}-evidence-${index}`}>{item}</li>
          ))}
        </ul>
        {check.evidenceView.rawText ? (
          <details className="check-raw-toggle">
            <summary>查看原始输出</summary>
            <pre className="check-raw-evidence">{check.evidenceView.rawText}</pre>
          </details>
        ) : null}
      </div>
    );
  }

  const evidenceText = check.evidenceView.summary ?? check.evidence;
  return (
    <p className="check-detail">
      <strong>核查证据：</strong>
      {evidenceText || "--"}
    </p>
  );
}
