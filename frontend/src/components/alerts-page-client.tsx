"use client";

import { useEffect, useState } from "react";

import {
  type AlertItem,
  formatAlertStatus,
  formatDateTime,
  formatRiskLevel,
} from "@/lib/inspection-view";

type AlertsPageClientProps = {
  alerts: AlertItem[];
};

export function AlertsPageClient({ alerts }: AlertsPageClientProps) {
  const [severityFilter, setSeverityFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState(alerts[0]?.id ?? "");

  const filteredAlerts = alerts.filter((alert) => {
    const keyword = search.trim().toLowerCase();
    const matchesKeyword =
      keyword.length === 0 ||
      alert.title.toLowerCase().includes(keyword) ||
      alert.assetName.toLowerCase().includes(keyword) ||
      alert.assetIp.includes(keyword);
    const matchesSeverity = severityFilter === "all" || alert.severity === severityFilter;

    return matchesKeyword && matchesSeverity;
  });

  useEffect(() => {
    if (!filteredAlerts.some((alert) => alert.id === selectedId)) {
      setSelectedId(filteredAlerts[0]?.id ?? "");
    }
  }, [filteredAlerts, selectedId]);

  const selectedAlert =
    filteredAlerts.find((alert) => alert.id === selectedId) ?? filteredAlerts[0] ?? null;

  return (
    <div className="content-grid with-sidebar">
      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>告警列表</h3>
            <p>当前告警由最新巡检失败项实时派生，不再展示测试告警。</p>
          </div>
          <div className="section-meta">当前 {filteredAlerts.length} 条</div>
        </div>

        <div className="filter-bar">
          <label className="filter-field filter-field-wide">
            <span>搜索</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索告警标题、资产名、IP"
            />
          </label>

          <label className="filter-field">
            <span>风险等级筛选</span>
            <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
              <option value="all">全部等级</option>
              <option value="high">高危</option>
              <option value="medium">中危</option>
            </select>
          </label>
        </div>

        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>终端告警</th>
                <th>严重程度</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.map((alert) => (
                <tr
                  key={alert.id}
                  className={selectedAlert?.id === alert.id ? "is-selected" : ""}
                  onClick={() => setSelectedId(alert.id)}
                >
                  <td>
                    <div className="cell-primary">
                      <span className={`cell-link-static text-glow-${alert.severity === "high" ? "red" : "yellow"}`}>
                        {formatAlertTerminalLine(alert)}
                      </span>
                      <span>
                        {alert.description} :: {alert.assetName}
                      </span>
                      <span className="mono">{alert.assetIp}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge tone-${alert.severity === "high" ? "critical" : "medium"}`}>
                      {formatRiskLevel(alert.severity === "high" ? "critical" : "medium")}
                    </span>
                  </td>
                  <td>
                    <span className="badge tone-info">{formatAlertStatus(alert.status)}</span>
                  </td>
                </tr>
              ))}

              {filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan={3}>
                    <div className="empty-inline">当前没有真实告警数据。</div>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="side-panel-card">
        <div className="section-head">
          <div>
            <h3>告警详情</h3>
            <p>默认展示当前选中告警的风险结论与来源资产。</p>
          </div>
        </div>

        {selectedAlert ? (
          <div className="detail-stack">
            <div className="headline-card">
              <div className="headline-row">
                <strong>{selectedAlert.title}</strong>
                <span className={`badge tone-${selectedAlert.severity === "high" ? "critical" : "medium"}`}>
                  {selectedAlert.severity === "high" ? "高危" : "中危"}
                </span>
              </div>
              <p>{selectedAlert.description}</p>
            </div>

            <div className="info-list">
              <div>
                <span>资产</span>
                <strong>{selectedAlert.assetName}</strong>
              </div>
              <div>
                <span>IP</span>
                <strong className="mono">{selectedAlert.assetIp}</strong>
              </div>
              <div>
                <span>状态</span>
                <strong>{formatAlertStatus(selectedAlert.status)}</strong>
              </div>
              <div>
                <span>检出时间</span>
                <strong>{formatDateTime(selectedAlert.detectedAt)}</strong>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-inline">当前没有告警数据。</div>
        )}
      </aside>
    </div>
  );
}

function formatAlertTerminalLine(alert: AlertItem): string {
  const marker = alert.severity === "high" ? "[!!!]" : "[!!]";
  const severity = alert.severity === "high" ? "HIGH" : "MEDIUM";
  return `[${formatDateTime(alert.detectedAt)}] ${marker} ${alert.title} :: ${alert.assetIp} :: ${severity}`;
}
