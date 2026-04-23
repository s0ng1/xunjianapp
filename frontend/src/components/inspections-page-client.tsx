"use client";

import { useState } from "react";

import {
  type InspectionListItem,
  formatDateTime,
  formatInspectionStatus,
  formatInspectionType,
} from "@/lib/inspection-view";

type InspectionsPageClientProps = {
  inspections: InspectionListItem[];
};

export function InspectionsPageClient({ inspections }: InspectionsPageClientProps) {
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  const filteredInspections = inspections.filter((inspection) => {
    const matchesStatus = statusFilter === "all" || inspection.status === statusFilter;
    const matchesType = typeFilter === "all" || inspection.type === typeFilter;
    return matchesStatus && matchesType;
  });

  return (
    <section className="panel-card">
      <div className="section-head">
        <div>
          <h3>巡检记录</h3>
          <p>当前只展示真实巡检、扫描和基线执行记录，不再展示测试记录。</p>
        </div>
        <div className="section-meta">共 {filteredInspections.length} 条</div>
      </div>

      <div className="filter-bar">
        <label className="filter-field">
          <span>巡检类型</span>
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="all">全部类型</option>
            <option value="linux">Linux 巡检</option>
            <option value="switch">交换机巡检</option>
            <option value="port_scan">端口扫描</option>
            <option value="baseline">基线检查</option>
          </select>
        </label>

        <label className="filter-field">
          <span>状态</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">全部状态</option>
            <option value="success">成功</option>
            <option value="partial">部分异常</option>
            <option value="failed">失败</option>
          </select>
        </label>
      </div>

      <div className="table-shell">
        <table className="data-table">
            <thead>
              <tr>
                <th>任务 ID</th>
                <th>资产</th>
                <th>巡检类型</th>
                <th>开始 / 结束时间</th>
                <th>状态</th>
                <th>进度</th>
                <th>结果摘要</th>
              </tr>
          </thead>
          <tbody>
            {filteredInspections.map((inspection) => (
              <tr key={inspection.id}>
                <td>
                  <div className="cell-primary">
                    <span className="mono">{inspection.id}</span>
                    <span>{inspection.operator}</span>
                  </div>
                </td>
                <td>
                  <div className="cell-primary">
                    <span>{inspection.assetName}</span>
                    <span className="mono">{inspection.assetIp}</span>
                  </div>
                </td>
                <td>{formatInspectionType(inspection.type)}</td>
                <td>
                  <div className="cell-primary">
                    <span>{formatDateTime(inspection.startedAt)}</span>
                    <span>结束 {inspection.duration}</span>
                  </div>
                </td>
                <td>
                  <span className={`badge tone-${mapInspectionStatusBadge(inspection.status)}`}>
                    {formatInspectionStatus(inspection.status)}
                  </span>
                </td>
                <td className="mono">{formatAsciiProgress(inspection.status)}</td>
                <td>
                  <div className="cell-primary">
                    <span>{inspection.summary}</span>
                    <span>{inspection.findings}</span>
                  </div>
                </td>
              </tr>
            ))}

            {filteredInspections.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-inline">当前没有真实巡检记录。</div>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function mapInspectionStatusBadge(status: InspectionListItem["status"]): "normal" | "medium" | "critical" {
  if (status === "success") {
    return "normal";
  }
  if (status === "partial") {
    return "medium";
  }
  return "critical";
}

function formatAsciiProgress(status: InspectionListItem["status"]): string {
  if (status === "success") {
    return "[██████████] 100%";
  }
  if (status === "partial") {
    return "[████████░░] 80%";
  }
  return "[██░░░░░░░░] 20%";
}
