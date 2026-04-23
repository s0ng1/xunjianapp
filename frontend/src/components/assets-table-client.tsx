"use client";

import Link from "next/link";
import { useState } from "react";

import {
  type AssetOverview,
  formatAssetType,
  formatDateTime,
} from "@/lib/inspection-view";

type AssetsTableClientProps = {
  assets: AssetOverview[];
  selectedAssetId: number | null;
  onRequestAction: (assetId: number, action: "edit" | "ssh" | "port_scan" | "inspect" | "baseline") => void;
};

export function AssetsTableClient({ assets, selectedAssetId, onRequestAction }: AssetsTableClientProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");

  const filteredAssets = assets.filter((item) => {
    const keyword = search.trim().toLowerCase();
    const matchesKeyword =
      keyword.length === 0 ||
      item.asset.name.toLowerCase().includes(keyword) ||
      item.asset.ip.includes(keyword) ||
      item.asset.type.toLowerCase().includes(keyword);

    const matchesType = typeFilter === "all" || item.asset.type === typeFilter;
    const matchesStatus = statusFilter === "all" || item.statusTone === statusFilter;
    const matchesRisk = riskFilter === "all" || getOverviewRiskTone(item) === riskFilter;

    return matchesKeyword && matchesType && matchesStatus && matchesRisk;
  });

  return (
    <section className="panel-card primary-table-card">
      <div className="section-head">
        <div>
          <h3>资产列表</h3>
          <p>先在列表核对台账状态，再直接从行内入口发起编辑接入、SSH 预检、巡检和基线核查。</p>
        </div>
        <div className="section-meta">共 {filteredAssets.length} 台</div>
      </div>

      <div className="filter-bar">
        <label className="filter-field filter-field-wide">
          <span>搜索框</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索资产名、IP、类型"
          />
        </label>

        <label className="filter-field">
          <span>类型筛选</span>
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="all">全部类型</option>
            <option value="linux">Linux 服务器</option>
            <option value="switch">交换机</option>
          </select>
        </label>

        <label className="filter-field">
          <span>状态筛选</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">全部状态</option>
            <option value="healthy">稳定</option>
            <option value="warning">需关注</option>
            <option value="critical">高风险</option>
            <option value="unknown">未巡检</option>
          </select>
        </label>

        <label className="filter-field">
          <span>风险筛选</span>
          <select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
            <option value="all">全部风险</option>
            <option value="critical">高危</option>
            <option value="medium">中危</option>
            <option value="normal">无风险</option>
          </select>
        </label>
      </div>

      <div className="table-shell">
        <table className="data-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>IP</th>
              <th>类型</th>
              <th>接入</th>
              <th>状态</th>
              <th>风险</th>
              <th>最近巡检</th>
              <th>执行</th>
            </tr>
          </thead>
          <tbody>
            {filteredAssets.map((item) => {
              const riskTone = getOverviewRiskTone(item);
              const isSelected = item.asset.id === selectedAssetId;

              return (
                <tr key={item.asset.id} className={isSelected ? "is-selected" : undefined}>
                  <td>
                    <div className="cell-primary">
                      <Link href={`/assets/${item.asset.id}`} className="cell-link">
                        {item.asset.name}
                      </Link>
                      {item.supportsHistory ? (
                        <Link href={`/assets/${item.asset.id}`} className="table-detail-link">
                          查看巡检详情
                        </Link>
                      ) : (
                        <span>当前无详情支持</span>
                      )}
                    </div>
                  </td>
                  <td className="mono">{item.asset.ip}</td>
                  <td>{formatAssetType(item.asset.type)}</td>
                  <td>
                    <div className="cell-primary">
                      <span
                        className={`badge tone-${item.asset.credential_configured ? "normal" : "info"}`}
                      >
                        {item.asset.credential_configured ? "凭据已配置" : "凭据缺失"}
                      </span>
                      <span>
                        {item.asset.connection_type.toUpperCase()} / 端口 {item.asset.port}
                      </span>
                      <button
                        className="table-action-link"
                        type="button"
                        onClick={() => onRequestAction(item.asset.id, "edit")}
                      >
                        编辑用户名 / 密码
                      </button>
                    </div>
                  </td>
                  <td>
                    <span className={`badge tone-${mapOverviewStatusBadge(item.statusTone)}`}>{item.statusLabel}</span>
                  </td>
                  <td>
                    <div className="cell-primary">
                      <span className={`badge tone-${mapOverviewRiskBadge(riskTone)}`}>
                        {item.riskCount} 项 / {formatOverviewRisk(riskTone)}
                      </span>
                      <span>高危 {item.highRiskCount} / 中危 {item.mediumRiskCount}</span>
                    </div>
                  </td>
                  <td>
                    <div className="cell-primary">
                      <span>{formatDateTime(item.lastInspectionAt)}</span>
                      <span
                        className="cell-summary-line"
                        title={item.latestInspection?.message ?? "当前还没有巡检结果"}
                      >
                        {summarizeInspectionMessage(item.latestInspection?.message)}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="row-action-group" aria-label={`${item.asset.name} 执行动作`}>
                      <button
                        className="row-action-button"
                        type="button"
                        onClick={() => onRequestAction(item.asset.id, "ssh")}
                      >
                        SSH
                      </button>
                      <button
                        className="row-action-button"
                        type="button"
                        onClick={() => onRequestAction(item.asset.id, "port_scan")}
                      >
                        端口
                      </button>
                      <button
                        className="row-action-button"
                        type="button"
                        onClick={() => onRequestAction(item.asset.id, "inspect")}
                      >
                        巡检
                      </button>
                      <button
                        className="row-action-button"
                        type="button"
                        onClick={() => onRequestAction(item.asset.id, "baseline")}
                      >
                        基线
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}

            {filteredAssets.length === 0 ? (
              <tr>
                <td colSpan={8}>
                  <div className="empty-inline">当前没有真实资产数据，或筛选条件下没有匹配项。</div>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function summarizeInspectionMessage(message: string | null | undefined): string {
  if (!message) {
    return "当前还没有巡检结果";
  }

  const compact = message.replace(/\s+/g, " ").trim();
  if (compact.length <= 34) {
    return compact;
  }

  return `${compact.slice(0, 34)}...`;
}

function getOverviewRiskTone(item: AssetOverview): "critical" | "medium" | "normal" {
  if (item.highRiskCount > 0) {
    return "critical";
  }
  if (item.mediumRiskCount > 0) {
    return "medium";
  }
  return "normal";
}

function mapOverviewStatusBadge(statusTone: AssetOverview["statusTone"]): "critical" | "medium" | "normal" | "info" {
  if (statusTone === "critical") {
    return "critical";
  }
  if (statusTone === "warning") {
    return "medium";
  }
  if (statusTone === "healthy") {
    return "normal";
  }
  return "info";
}

function mapOverviewRiskBadge(riskTone: "critical" | "medium" | "normal"): "critical" | "medium" | "normal" {
  return riskTone;
}

function formatOverviewRisk(riskTone: "critical" | "medium" | "normal"): string {
  if (riskTone === "critical") {
    return "高危";
  }
  if (riskTone === "medium") {
    return "中危";
  }
  return "无风险";
}
