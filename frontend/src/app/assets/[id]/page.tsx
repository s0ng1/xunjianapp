import Link from "next/link";
import { notFound } from "next/navigation";

import { DetailSections } from "@/components/detail-sections";
import { DashboardShell } from "@/components/dashboard-shell";
import { StatePanel } from "@/components/state-panel";
import {
  fetchAssets,
  fetchLinuxInspections,
  fetchSwitchInspections,
} from "@/lib/api";
import {
  buildAssetDetailView,
  formatAssetType,
  formatDateTime,
} from "@/lib/inspection-view";

type AssetDetailPageProps = {
  params: {
    id: string;
  };
};

export default async function AssetDetailPage({ params }: AssetDetailPageProps) {
  const assetId = Number(params.id);

  if (!Number.isInteger(assetId)) {
    notFound();
  }

  try {
    const [assetsResult, linuxResult, switchResult] = await Promise.allSettled([
      fetchAssets(),
      fetchLinuxInspections(),
      fetchSwitchInspections(),
    ]);

    if (assetsResult.status !== "fulfilled") {
      return (
        <DashboardShell
          activePath="/assets"
          badge="设备详情"
          title="资产详情"
          description="当前无法获取真实详情数据。"
        >
          <StatePanel
            tone="error"
            title="资产详情加载失败"
            description="资产台账接口当前不可用，请检查后端服务状态后重试。"
            action={{ href: "/assets", label: "返回资产列表" }}
          />
        </DashboardShell>
      );
    }

    const asset = assetsResult.value.find((item) => item.id === assetId);
    if (!asset) {
      notFound();
    }

    const linuxInspections = linuxResult.status === "fulfilled" ? linuxResult.value : [];
    const switchInspections = switchResult.status === "fulfilled" ? switchResult.value : [];
    const detail = buildAssetDetailView(asset, linuxInspections, switchInspections);
    const detailNotice = buildAssetDetailLoadNotice({
      assetType: asset.type,
      linuxInspectionAvailable: linuxResult.status === "fulfilled",
      switchInspectionAvailable: switchResult.status === "fulfilled",
    });

    return (
      <DashboardShell
        activePath="/assets"
        badge="设备详情"
        title={asset.name}
        description="详情页展示真实巡检结果和后端派生风险。"
      >
        <section className="panel-card">
          <div className="section-head">
            <div>
              <h3>基本信息</h3>
              <p>当前信息全部来自真实资产台账与巡检结果。</p>
            </div>
            <Link href="/assets" className="text-action">
              返回资产列表
            </Link>
          </div>

          <div className="info-grid">
            <article className="info-card">
              <span>资产名称</span>
              <strong>{asset.name}</strong>
              <p>ID {asset.id}</p>
            </article>
            <article className="info-card">
              <span>IP 地址</span>
              <strong className="mono">{asset.ip}</strong>
              <p>纳管对象</p>
            </article>
            <article className="info-card">
              <span>资产类型</span>
              <strong>{formatAssetType(asset.type)}</strong>
              <p>按资产类型自动匹配巡检来源</p>
            </article>
            <article className="info-card">
              <span>接入配置</span>
              <strong>{asset.connection_type.toUpperCase()} / {asset.port}</strong>
              <p>{asset.username ?? "未配置用户名"}</p>
            </article>
            <article className="info-card">
              <span>凭据状态</span>
              <strong>{asset.credential_configured ? "已配置" : "未配置"}</strong>
              <p>{asset.is_enabled ? "资产已启用" : "资产已停用"}</p>
            </article>
            <article className="info-card">
              <span>最近巡检</span>
              <strong>{formatDateTime(detail.lastInspectionAt)}</strong>
              <p>{detail.latestInspection?.message ?? "当前没有巡检记录"}</p>
            </article>
            <article className="info-card">
              <span>纳管时间</span>
              <strong>{formatDateTime(asset.created_at)}</strong>
              <p>来自后端资产接口</p>
            </article>
            <article className="info-card">
              <span>当前状态</span>
              <strong>{detail.statusLabel}</strong>
              <p>根据最近一次巡检自动计算</p>
            </article>
          </div>
        </section>

        {detailNotice ? (
          <StatePanel
            tone={detailNotice.tone}
            title={detailNotice.title}
            description={detailNotice.description}
          />
        ) : null}

        <DetailSections detail={detail} />

        {detail.rawOutputs.length > 0 ? (
          <section className="section-card">
            <div className="section-header">
              <div>
                <h3 className="section-title">原始输出</h3>
                <p className="section-description">
                  展示后端返回的最近一次巡检原始文本，默认折叠。
                </p>
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
          </section>
        ) : null}
      </DashboardShell>
    );
  } catch (error) {
    console.error("Asset detail page failed:", error);

    return (
      <DashboardShell
        activePath="/assets"
        badge="设备详情"
        title="资产详情"
        description="当前无法获取真实详情数据。"
      >
        <StatePanel
          tone="error"
          title="资产详情加载失败"
          description="页面在整理资产详情时遇到异常，请稍后重试。"
          action={{ href: "/assets", label: "返回资产列表" }}
        />
      </DashboardShell>
    );
  }
}

function buildAssetDetailLoadNotice({
  assetType,
  linuxInspectionAvailable,
  switchInspectionAvailable,
}: {
  assetType: string;
  linuxInspectionAvailable: boolean;
  switchInspectionAvailable: boolean;
}): { tone: "info"; title: string; description: string } | null {
  if (assetType === "linux" && !linuxInspectionAvailable) {
    return {
      tone: "info",
      title: "Linux 巡检记录暂不可用",
      description: "当前详情页只展示资产台账信息，最近巡检、风险和原始输出需要待 Linux 巡检接口恢复后再核对。",
    };
  }

  if (assetType === "switch" && !switchInspectionAvailable) {
    return {
      tone: "info",
      title: "交换机巡检记录暂不可用",
      description: "当前详情页只展示资产台账信息，最近巡检、风险和原始输出需要待交换机巡检接口恢复后再核对。",
    };
  }

  return null;
}
