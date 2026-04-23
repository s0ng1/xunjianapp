"use client";

import { useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from "react";

import { StatePanel } from "@/components/state-panel";
import type { Asset, BaselineRun, LinuxInspection, SwitchInspection } from "@/lib/api";
import { fetchLinuxInspections, fetchSwitchInspections, runAssetInspection } from "@/lib/api";

import { AssetSelector, InspectionCard, SelectedAssetSummary } from "./operation-panel-shared";

type LinuxInspectionPanelProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  selectedAsset: Asset | null;
  canRunAssetSsh: boolean;
  onSelectedAssetChange: (assetId: number | null) => void;
  onLinuxInspectionsChange: Dispatch<SetStateAction<LinuxInspection[]>>;
  onSwitchInspectionsChange: Dispatch<SetStateAction<SwitchInspection[]>>;
  stageHeader: ReactNode;
};

export function LinuxInspectionPanel({
  assets,
  selectedAssetId,
  selectedAsset,
  canRunAssetSsh,
  onSelectedAssetChange,
  onLinuxInspectionsChange,
  onSwitchInspectionsChange,
  stageHeader,
}: LinuxInspectionPanelProps) {
  const [inspectionResult, setInspectionResult] = useState<BaselineRun | null>(null);
  const [inspectionError, setInspectionError] = useState<string | null>(null);
  const [inspectionBusy, setInspectionBusy] = useState(false);

  async function handleAssetInspection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedAsset == null) {
      setInspectionError("请先选择资产。");
      return;
    }
    setInspectionBusy(true);
    setInspectionError(null);

    try {
      const result = await runAssetInspection(selectedAsset.id);
      setInspectionResult(result);
      await refreshInspectionState(result.device_type);
    } catch (error) {
      setInspectionError(error instanceof Error ? error.message : "Inspection failed");
    } finally {
      setInspectionBusy(false);
    }
  }

  async function refreshInspectionState(deviceType: string) {
    if (deviceType === "linux") {
      onLinuxInspectionsChange(await fetchLinuxInspections());
      return;
    }
    if (deviceType === "switch") {
      onSwitchInspectionsChange(await fetchSwitchInspections());
    }
  }

  return (
    <section className="operation-stage-card">
      {stageHeader}
      <p className="operation-stage-description">根据当前资产类型自动进入 Linux 或交换机巡检，并把最新结果写回资产。</p>
      <form className="control-form" onSubmit={handleAssetInspection}>
        <AssetSelector
          assets={assets}
          selectedAssetId={selectedAssetId}
          onSelectedAssetChange={onSelectedAssetChange}
        />
        <SelectedAssetSummary asset={selectedAsset} />
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={inspectionBusy || !canRunAssetSsh}>
            {inspectionBusy ? "巡检中..." : "执行资产巡检"}
          </button>
        </div>
      </form>
      {!canRunAssetSsh ? (
        <StatePanel tone="info" title="当前资产还不能直接巡检" description="需要启用资产并补齐 SSH 用户名和凭据。" />
      ) : null}
      {inspectionError ? <StatePanel tone="error" title="资产巡检失败" description={inspectionError} /> : null}
      {inspectionResult ? (
        <InspectionCard
          title={`巡检结果 #${inspectionResult.inspection_id}`}
          success={inspectionResult.success}
          message={inspectionResult.message}
          baselineResults={inspectionResult.baseline_results}
          vendor={inspectionResult.vendor ?? undefined}
        />
      ) : null}
    </section>
  );
}
