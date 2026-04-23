"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import { StatePanel } from "@/components/state-panel";
import type { Asset, PortScanResult } from "@/lib/api";
import { runAssetPortScan } from "@/lib/api";

import { AssetSelector, ResultCard, SelectedAssetSummary } from "./operation-panel-shared";

type PortScanForm = {
  ports: string;
};

type PortScanPanelProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  selectedAsset: Asset | null;
  canRunAssetScan: boolean;
  onSelectedAssetChange: (assetId: number | null) => void;
  stageHeader: ReactNode;
};

const INITIAL_PORT_SCAN_FORM: PortScanForm = {
  ports: "22,80,443",
};

export function PortScanPanel({
  assets,
  selectedAssetId,
  selectedAsset,
  canRunAssetScan,
  onSelectedAssetChange,
  stageHeader,
}: PortScanPanelProps) {
  const [portScanForm, setPortScanForm] = useState(INITIAL_PORT_SCAN_FORM);
  const [portScanResult, setPortScanResult] = useState<PortScanResult | null>(null);
  const [portScanError, setPortScanError] = useState<string | null>(null);
  const [portScanBusy, setPortScanBusy] = useState(false);

  async function handleAssetPortScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedAsset == null) {
      setPortScanError("请先选择资产。");
      return;
    }
    setPortScanBusy(true);
    setPortScanError(null);

    try {
      setPortScanResult(
        await runAssetPortScan(selectedAsset.id, {
          ports: parsePorts(portScanForm.ports),
        }),
      );
    } catch (error) {
      setPortScanError(error instanceof Error ? error.message : "Port scan failed");
    } finally {
      setPortScanBusy(false);
    }
  }

  return (
    <section className="operation-stage-card">
      {stageHeader}
      <p className="operation-stage-description">直接针对当前资产运行端口扫描，并把扫描记录挂回资产。</p>
      <form className="control-form" onSubmit={handleAssetPortScan}>
        <AssetSelector
          assets={assets}
          selectedAssetId={selectedAssetId}
          onSelectedAssetChange={onSelectedAssetChange}
        />
        <SelectedAssetSummary asset={selectedAsset} />
        <div className="form-grid">
          <label className="field-stack field-span-2">
            <span className="field-label">扫描端口</span>
            <input
              className="control-input"
              value={portScanForm.ports}
              onChange={(event) => setPortScanForm((current) => ({ ...current, ports: event.target.value }))}
              placeholder="22,80,443"
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={portScanBusy || !canRunAssetScan}>
            {portScanBusy ? "扫描中..." : "执行端口扫描"}
          </button>
        </div>
      </form>
      {!canRunAssetScan ? (
        <StatePanel tone="info" title="当前资产不可执行" description="需要先选择一个启用中的资产。" />
      ) : null}
      {portScanError ? <StatePanel tone="error" title="端口扫描失败" description={portScanError} /> : null}
      {portScanResult ? (
        <ResultCard
          title={`扫描完成: ${portScanResult.ip}`}
          tone={portScanResult.open_ports.length > 0 ? "medium" : "good"}
          summary={`开放端口 ${portScanResult.open_ports.length} 个，检查端口 ${portScanResult.checked_ports.join(", ")}`}
          detail={portScanResult.message}
        />
      ) : null}
    </section>
  );
}

function parsePorts(value: string): number[] {
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((port) => Number.isInteger(port) && port > 0);
}
