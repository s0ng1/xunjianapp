"use client";

import { useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from "react";

import { StatePanel } from "@/components/state-panel";
import type { Asset, BaselineRun, LinuxInspection, SwitchInspection } from "@/lib/api";
import {
  fetchLinuxInspections,
  fetchSwitchInspections,
  rerunLinuxBaseline,
  rerunSwitchBaseline,
  runAssetBaseline,
} from "@/lib/api";

import { AssetSelector, InspectionCard, SelectedAssetSummary } from "./operation-panel-shared";

type RerunForm = {
  deviceType: "linux" | "switch";
  inspectionId: string;
};

type BaselineRunPanelProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  selectedAsset: Asset | null;
  canRunAssetSsh: boolean;
  onSelectedAssetChange: (assetId: number | null) => void;
  onLinuxInspectionsChange: Dispatch<SetStateAction<LinuxInspection[]>>;
  onSwitchInspectionsChange: Dispatch<SetStateAction<SwitchInspection[]>>;
  stageHeader: ReactNode;
  mode?: "asset" | "rerun";
};

const INITIAL_RERUN_FORM: RerunForm = {
  deviceType: "linux",
  inspectionId: "",
};

export function BaselineRunPanel({
  assets,
  selectedAssetId,
  selectedAsset,
  canRunAssetSsh,
  onSelectedAssetChange,
  onLinuxInspectionsChange,
  onSwitchInspectionsChange,
  stageHeader,
  mode = "asset",
}: BaselineRunPanelProps) {
  const [baselineResult, setBaselineResult] = useState<BaselineRun | null>(null);
  const [baselineError, setBaselineError] = useState<string | null>(null);
  const [baselineBusy, setBaselineBusy] = useState(false);
  const [rerunForm, setRerunForm] = useState(INITIAL_RERUN_FORM);
  const [rerunResult, setRerunResult] = useState<BaselineRun | null>(null);
  const [rerunError, setRerunError] = useState<string | null>(null);
  const [rerunBusy, setRerunBusy] = useState(false);

  async function handleAssetBaseline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedAsset == null) {
      setBaselineError("请先选择资产。");
      return;
    }
    setBaselineBusy(true);
    setBaselineError(null);

    try {
      const result = await runAssetBaseline(selectedAsset.id);
      setBaselineResult(result);
      await refreshInspectionState(result.device_type);
    } catch (error) {
      setBaselineError(error instanceof Error ? error.message : "Baseline run failed");
    } finally {
      setBaselineBusy(false);
    }
  }

  async function handleBaselineRerun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRerunBusy(true);
    setRerunError(null);

    try {
      const inspectionId = Number(rerunForm.inspectionId);
      if (!Number.isInteger(inspectionId) || inspectionId <= 0) {
        throw new Error("Inspection ID must be a positive integer");
      }

      const result =
        rerunForm.deviceType === "linux"
          ? await rerunLinuxBaseline(inspectionId)
          : await rerunSwitchBaseline(inspectionId);
      setRerunResult(result);
      await refreshInspectionState(result.device_type);
    } catch (error) {
      setRerunError(error instanceof Error ? error.message : "Baseline rerun failed");
    } finally {
      setRerunBusy(false);
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

  if (mode === "rerun") {
    return (
      <section className="operation-stage-card">
        {stageHeader}
        <p className="operation-stage-description">按巡检记录 ID 单独重跑基线规则，不重新 SSH 登录设备。</p>
        <form className="control-form" onSubmit={handleBaselineRerun}>
          <div className="form-grid">
            <label className="field-stack">
              <span className="field-label">设备类型</span>
              <select
                className="control-select"
                value={rerunForm.deviceType}
                onChange={(event) =>
                  setRerunForm((current) => ({
                    ...current,
                    deviceType: event.target.value as "linux" | "switch",
                  }))
                }
              >
                <option value="linux">Linux</option>
                <option value="switch">Switch</option>
              </select>
            </label>
            <label className="field-stack">
              <span className="field-label">巡检记录 ID</span>
              <input
                className="control-input"
                value={rerunForm.inspectionId}
                onChange={(event) => setRerunForm((current) => ({ ...current, inspectionId: event.target.value }))}
                placeholder="12"
                required
              />
            </label>
          </div>
          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={rerunBusy}>
              {rerunBusy ? "重跑中..." : "重跑基线"}
            </button>
          </div>
        </form>
        {rerunError ? <StatePanel tone="error" title="基线重跑失败" description={rerunError} /> : null}
        {rerunResult ? (
          <InspectionCard
            title={`重跑结果 #${rerunResult.inspection_id}`}
            success={rerunResult.success}
            message={rerunResult.message}
            baselineResults={rerunResult.baseline_results}
            vendor={rerunResult.vendor ?? undefined}
          />
        ) : null}
      </section>
    );
  }

  return (
    <section className="operation-stage-card">
      {stageHeader}
      <p className="operation-stage-description">基线入口同样围绕当前资产执行，结果会自动落到对应巡检记录上。</p>
      <form className="control-form" onSubmit={handleAssetBaseline}>
        <AssetSelector
          assets={assets}
          selectedAssetId={selectedAssetId}
          onSelectedAssetChange={onSelectedAssetChange}
        />
        <SelectedAssetSummary asset={selectedAsset} />
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={baselineBusy || !canRunAssetSsh}>
            {baselineBusy ? "执行中..." : "运行基线检查"}
          </button>
        </div>
      </form>
      {!canRunAssetSsh ? (
        <StatePanel tone="info" title="当前资产还不能直接跑基线" description="需要启用资产并补齐 SSH 用户名和凭据。" />
      ) : null}
      {baselineError ? <StatePanel tone="error" title="基线执行失败" description={baselineError} /> : null}
      {baselineResult ? (
        <InspectionCard
          title={`基线结果 #${baselineResult.inspection_id}`}
          success={baselineResult.success}
          message={baselineResult.message}
          baselineResults={baselineResult.baseline_results}
          vendor={baselineResult.vendor ?? undefined}
        />
      ) : null}
    </section>
  );
}
