"use client";

import { useState } from "react";

import { AssetsTableClient } from "@/components/assets-table-client";
import { DashboardShell } from "@/components/dashboard-shell";
import { OperationsConsole } from "@/components/operations-console";
import { StatePanel } from "@/components/state-panel";
import type { Asset, LinuxInspection, SwitchInspection } from "@/lib/api";
import { buildAssetOverviewList, type AssetOverview } from "@/lib/inspection-view";

export type AssetListAction = "edit" | "ssh" | "port_scan" | "inspect" | "baseline";

export type AssetsPageLoadNotice = {
  key: string;
  tone: "info" | "error";
  title: string;
  description: string;
};

type AssetActionRequest = {
  assetId: number;
  action: AssetListAction;
  nonce: number;
};

type AssetsPageClientProps = {
  initialAssets: Asset[];
  linuxInspections: LinuxInspection[];
  switchInspections: SwitchInspection[];
  assetCatalogAvailable?: boolean;
  loadNotices?: AssetsPageLoadNotice[];
};

export function AssetsPageClient({
  initialAssets,
  linuxInspections,
  switchInspections,
  assetCatalogAvailable = true,
  loadNotices = [],
}: AssetsPageClientProps) {
  const [assets, setAssets] = useState(initialAssets);
  const [linuxInspectionState, setLinuxInspectionState] = useState(linuxInspections);
  const [switchInspectionState, setSwitchInspectionState] = useState(switchInspections);
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(initialAssets[0]?.id ?? null);
  const [actionRequest, setActionRequest] = useState<AssetActionRequest | null>(null);
  const assetOverview = buildAssetOverviewList(assets, linuxInspectionState, switchInspectionState);

  function handleAssetAction(assetId: number, action: AssetListAction) {
    setSelectedAssetId(assetId);
    setActionRequest({ assetId, action, nonce: Date.now() });

    if (typeof window === "undefined") {
      return;
    }

    const targetId = action === "edit" ? "asset-management-section" : "asset-execution-section";
    window.requestAnimationFrame(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <DashboardShell
      activePath="/assets"
      badge="资产台账"
      title="资产列表"
      description="先在台账里核对状态，再从列表直接发起接入维护、巡检和基线动作。"
      summary={buildAssetPageSummary(assetOverview, assetCatalogAvailable)}
      stats={buildAssetPageStats(assetOverview, assetCatalogAvailable)}
    >
      <div className="page-stack">
        {loadNotices.map((notice) => (
          <StatePanel
            key={notice.key}
            tone={notice.tone}
            title={notice.title}
            description={notice.description}
          />
        ))}
        <AssetsTableClient
          assets={assetOverview}
          selectedAssetId={selectedAssetId}
          onRequestAction={handleAssetAction}
        />
        <section className="support-intro" aria-label="资产辅助动作区">
          <span className="support-kicker">辅助动作区</span>
          <h2>执行动作</h2>
          <p>列表中的行内动作会把资产带入这里继续处理，SSH、扫描、巡检和基线都从资产配置出发，不再重复手填 IP 和密码。</p>
        </section>
        <OperationsConsole
          assets={assets}
          selectedAssetId={selectedAssetId}
          actionRequest={actionRequest}
          onSelectedAssetChange={setSelectedAssetId}
          onAssetsChange={setAssets}
          onLinuxInspectionsChange={setLinuxInspectionState}
          onSwitchInspectionsChange={setSwitchInspectionState}
        />
      </div>
    </DashboardShell>
  );
}

function buildAssetPageStats(assets: AssetOverview[], assetCatalogAvailable: boolean) {
  if (!assetCatalogAvailable) {
    return [
      {
        label: "已纳管资产",
        value: "--",
        conclusion: "资产台账接口当前不可用，暂时无法统计纳管规模。",
        tone: "medium" as const,
        statusText: "加载失败",
      },
      {
        label: "高风险资产",
        value: "--",
        conclusion: "待资产台账恢复后再核对高风险资产归属。",
        tone: "info" as const,
        statusText: "待恢复",
      },
      {
        label: "需关注资产",
        value: "--",
        conclusion: "当前列表已降级为空台账，风险统计暂不可信。",
        tone: "info" as const,
        statusText: "统计暂停",
      },
      {
        label: "待巡检资产",
        value: "--",
        conclusion: "资产清单未成功加载，暂时无法判断覆盖情况。",
        tone: "info" as const,
        statusText: "无法统计",
      },
    ];
  }

  const isEmpty = assets.length === 0;
  const criticalCount = assets.filter((item) => item.statusTone === "critical").length;
  const warningCount = assets.filter((item) => item.statusTone === "warning").length;
  const unknownCount = assets.filter((item) => item.statusTone === "unknown").length;
  const linuxCount = assets.filter((item) => item.asset.type.toLowerCase() === "linux").length;

  return [
    {
      label: "已纳管资产",
      value: String(assets.length),
      conclusion: assets.length > 0 ? `当前纳管 Linux ${linuxCount} 台` : "当前还没有纳管资产",
      tone: assets.length > 0 ? ("info" as const) : ("medium" as const),
      statusText: assets.length > 0 ? "台账在线" : "待录入",
    },
    {
      label: "高风险资产",
      value: String(criticalCount),
      conclusion: criticalCount > 0 ? `优先核对 ${criticalCount} 台高风险资产` : "当前没有高风险资产",
      tone: criticalCount > 0 ? ("critical" as const) : ("normal" as const),
      statusText: criticalCount > 0 ? "需优先处理" : "当前稳定",
    },
    {
      label: "需关注资产",
      value: String(warningCount),
      conclusion: warningCount > 0 ? `仍有 ${warningCount} 台资产存在中危或异常项` : "当前没有需关注资产",
      tone: warningCount > 0 ? ("medium" as const) : ("normal" as const),
      statusText: warningCount > 0 ? "待排查" : "已清空",
    },
    {
      label: "待巡检资产",
      value: String(unknownCount),
      conclusion: isEmpty
        ? "当前没有资产，尚未进入巡检覆盖阶段"
        : unknownCount > 0
          ? `仍有 ${unknownCount} 台资产缺少最近巡检结果`
          : "全部资产都有最近结果",
      tone: isEmpty ? ("info" as const) : unknownCount > 0 ? ("low" as const) : ("normal" as const),
      statusText: isEmpty ? "尚未开始" : unknownCount > 0 ? "待补齐" : "结果完整",
    },
  ];
}

function buildAssetPageSummary(assets: AssetOverview[], assetCatalogAvailable: boolean) {
  if (!assetCatalogAvailable) {
    return "资产台账当前未成功加载，页面已保留录入和执行区域，但列表与统计结果暂不可信。";
  }

  if (assets.length === 0) {
    return "当前还没有纳管资产，先录入资产，再从台账列表进入后续排查动作。";
  }

  const criticalCount = assets.filter((item) => item.statusTone === "critical").length;
  if (criticalCount > 0) {
    return `当前有 ${criticalCount} 台资产处于高风险状态，首屏应先核对台账与最近一次巡检摘要。`;
  }

  const warningCount = assets.filter((item) => item.statusTone === "warning").length;
  if (warningCount > 0) {
    return `当前没有高风险资产，但仍有 ${warningCount} 台资产需要关注，先在列表中确认风险分布与最近结果。`;
  }

  const unknownCount = assets.filter((item) => item.statusTone === "unknown").length;
  if (unknownCount > 0) {
    return `当前风险整体可控，但仍有 ${unknownCount} 台资产尚未产生巡检结果，需要补齐巡检留痕。`;
  }

  return "当前台账状态平稳，首屏优先核对资产清单、状态和最近巡检时间。";
}
