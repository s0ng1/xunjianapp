"use client";

import { useEffect, useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from "react";

import { StatePanel } from "@/components/state-panel";
import type { Asset, LinuxInspection, SwitchInspection } from "@/lib/api";
import { fetchSwitchInspections } from "@/lib/api";
import { apiSubmitSwitchInspection } from "@/lib/api/switch-inspections";

import { AssetSelector, ResultCard, SelectedAssetSummary } from "./operation-panel-shared";

type SwitchInspectionForm = {
  ip: string;
  username: string;
  password: string;
  port: string;
  vendor: "h3c";
};

type SwitchInspectionPanelProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  selectedAsset: Asset | null;
  canRunAssetSsh: boolean;
  onSelectedAssetChange: (assetId: number | null) => void;
  onLinuxInspectionsChange: Dispatch<SetStateAction<LinuxInspection[]>>;
  onSwitchInspectionsChange: Dispatch<SetStateAction<SwitchInspection[]>>;
  stageHeader: ReactNode;
};

const INITIAL_SWITCH_INSPECTION_FORM: SwitchInspectionForm = {
  ip: "",
  username: "",
  password: "",
  port: "22",
  vendor: "h3c",
};

export function SwitchInspectionPanel({
  assets,
  selectedAssetId,
  selectedAsset,
  canRunAssetSsh: _canRunAssetSsh,
  onSelectedAssetChange,
  onLinuxInspectionsChange: _onLinuxInspectionsChange,
  onSwitchInspectionsChange,
  stageHeader,
}: SwitchInspectionPanelProps) {
  const [switchInspectionForm, setSwitchInspectionForm] = useState<SwitchInspectionForm>(INITIAL_SWITCH_INSPECTION_FORM);
  const [switchInspectionResult, setSwitchInspectionResult] = useState<SwitchInspection | null>(null);
  const [switchInspectionError, setSwitchInspectionError] = useState<string | null>(null);
  const [switchInspectionBusy, setSwitchInspectionBusy] = useState(false);

  useEffect(() => {
    if (selectedAsset == null) {
      setSwitchInspectionForm(INITIAL_SWITCH_INSPECTION_FORM);
      return;
    }

    setSwitchInspectionForm({
      ip: selectedAsset.ip,
      username: selectedAsset.username ?? "",
      password: "",
      port: String(selectedAsset.port || 22),
      vendor: "h3c",
    });
  }, [selectedAsset]);

  async function handleSwitchInspection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSwitchInspectionBusy(true);
    setSwitchInspectionError(null);

    try {
      const payload = {
        ip: switchInspectionForm.ip.trim(),
        username: switchInspectionForm.username.trim(),
        password: switchInspectionForm.password,
        vendor: switchInspectionForm.vendor,
        port: Number(switchInspectionForm.port) || 22,
      };
      const result = await apiSubmitSwitchInspection(payload);
      setSwitchInspectionResult(result);
      onSwitchInspectionsChange(await fetchSwitchInspections());
    } catch (error) {
      setSwitchInspectionError(error instanceof Error ? error.message : "Switch inspection failed");
    } finally {
      setSwitchInspectionBusy(false);
    }
  }

  return (
    <section className="operation-stage-card">
      {stageHeader}
      <p className="operation-stage-description">填写交换机 SSH 参数后直接发起巡检，当前默认走 H3C 流程并展示原始配置。</p>
      <form className="control-form" onSubmit={handleSwitchInspection}>
        <AssetSelector
          assets={assets}
          selectedAssetId={selectedAssetId}
          onSelectedAssetChange={onSelectedAssetChange}
        />
        <SelectedAssetSummary asset={selectedAsset} />
        <div className="form-grid">
          <label className="field-stack">
            <span className="field-label">IP 地址</span>
            <input
              className="control-input"
              type="text"
              value={switchInspectionForm.ip}
              onChange={(event) => setSwitchInspectionForm((current) => ({ ...current, ip: event.target.value }))}
              placeholder="192.168.1.2"
              required
            />
          </label>
          <label className="field-stack">
            <span className="field-label">端口</span>
            <input
              className="control-input"
              type="number"
              min="1"
              max="65535"
              value={switchInspectionForm.port}
              onChange={(event) => setSwitchInspectionForm((current) => ({ ...current, port: event.target.value }))}
              placeholder="22"
            />
          </label>
          <label className="field-stack">
            <span className="field-label">用户名</span>
            <input
              className="control-input"
              type="text"
              value={switchInspectionForm.username}
              onChange={(event) => setSwitchInspectionForm((current) => ({ ...current, username: event.target.value }))}
              placeholder="admin"
              required
            />
          </label>
          <label className="field-stack">
            <span className="field-label">厂商</span>
            <select
              className="control-select"
              value={switchInspectionForm.vendor}
              onChange={(event) =>
                setSwitchInspectionForm((current) => ({ ...current, vendor: event.target.value as "h3c" }))
              }
            >
              <option value="h3c">H3C</option>
            </select>
          </label>
          <label className="field-stack field-span-2">
            <span className="field-label">密码</span>
            <input
              className="control-input"
              type="password"
              value={switchInspectionForm.password}
              onChange={(event) => setSwitchInspectionForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="输入本次巡检使用的密码"
              required
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={switchInspectionBusy}>
            {switchInspectionBusy ? "巡检中..." : "执行交换机巡检"}
          </button>
        </div>
      </form>
      {switchInspectionError ? (
        <StatePanel tone="error" title="交换机巡检失败" description={switchInspectionError} />
      ) : null}
      {switchInspectionResult ? (
        <div className="result-stack">
          <ResultCard
            title={`交换机巡检 #${switchInspectionResult.id} / ${switchInspectionResult.vendor}`}
            tone={switchInspectionResult.success ? "good" : "high"}
            summary={switchInspectionResult.success ? "巡检完成" : "巡检失败"}
            detail={switchInspectionResult.message}
          />
          <details className="panel-card">
            <summary>查看原始配置</summary>
            <pre className="mono" style={{ whiteSpace: "pre-wrap", marginTop: "1rem" }}>
              {switchInspectionResult.raw_config?.trim() || "未返回原始配置。"}
            </pre>
          </details>
        </div>
      ) : null}
    </section>
  );
}
