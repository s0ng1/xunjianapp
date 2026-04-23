import { AssetsPageClient } from "@/components/assets-page-client";
import type { AssetsPageLoadNotice } from "@/components/assets-page-client";
import {
  fetchAssets,
  fetchLinuxInspections,
  fetchSwitchInspections,
} from "@/lib/api";

export default async function AssetsPage() {
  const [assetsResult, linuxResult, switchResult] = await Promise.allSettled([
    fetchAssets(),
    fetchLinuxInspections(),
    fetchSwitchInspections(),
  ]);

  const assetCatalogAvailable = assetsResult.status === "fulfilled";
  const assets = assetsResult.status === "fulfilled" ? assetsResult.value : [];
  const linuxInspections = linuxResult.status === "fulfilled" ? linuxResult.value : [];
  const switchInspections = switchResult.status === "fulfilled" ? switchResult.value : [];
  const loadNotices = buildAssetsPageLoadNotices({
    assetCatalogAvailable,
    linuxInspectionAvailable: linuxResult.status === "fulfilled",
    switchInspectionAvailable: switchResult.status === "fulfilled",
  });

  return (
    <AssetsPageClient
      initialAssets={assets}
      linuxInspections={linuxInspections}
      switchInspections={switchInspections}
      assetCatalogAvailable={assetCatalogAvailable}
      loadNotices={loadNotices}
    />
  );
}

function buildAssetsPageLoadNotices({
  assetCatalogAvailable,
  linuxInspectionAvailable,
  switchInspectionAvailable,
}: {
  assetCatalogAvailable: boolean;
  linuxInspectionAvailable: boolean;
  switchInspectionAvailable: boolean;
}): AssetsPageLoadNotice[] {
  const notices: AssetsPageLoadNotice[] = [];

  if (!assetCatalogAvailable) {
    notices.push({
      key: "assets-unavailable",
      tone: "error",
      title: "资产台账暂不可用",
      description:
        "资产列表接口当前没有成功返回数据，页面已降级为空台账。你仍可继续新增资产，但既有资产、编辑入口和统计结果需要等后端恢复后再核对。",
    });
  }

  if (!linuxInspectionAvailable && !switchInspectionAvailable) {
    notices.push({
      key: "all-inspections-unavailable",
      tone: "info",
      title: "巡检结果暂不可用",
      description:
        "Linux 与交换机巡检记录都没有成功加载，资产状态、风险和最近巡检时间会按空结果降级展示。",
    });
    return notices;
  }

  if (!linuxInspectionAvailable) {
    notices.push({
      key: "linux-inspections-unavailable",
      tone: "info",
      title: "Linux 巡检记录未加载",
      description: "Linux 资产的状态、风险和最近巡检时间可能不完整，请在后端恢复后重新核对。",
    });
  }

  if (!switchInspectionAvailable) {
    notices.push({
      key: "switch-inspections-unavailable",
      tone: "info",
      title: "交换机巡检记录未加载",
      description: "交换机资产的状态、风险和最近巡检时间可能不完整，请在后端恢复后重新核对。",
    });
  }

  return notices;
}
