"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import { StatePanel } from "@/components/state-panel";
import type { Asset, SSHTestResult } from "@/lib/api";
import { runAssetSshTest } from "@/lib/api";

import { AssetSelector, ResultCard, SelectedAssetSummary } from "./operation-panel-shared";

type SshTestPanelProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  selectedAsset: Asset | null;
  canRunAssetSsh: boolean;
  onSelectedAssetChange: (assetId: number | null) => void;
  stageHeader: ReactNode;
};

export function SshTestPanel({
  assets,
  selectedAssetId,
  selectedAsset,
  canRunAssetSsh,
  onSelectedAssetChange,
  stageHeader,
}: SshTestPanelProps) {
  const [sshResult, setSshResult] = useState<SSHTestResult | null>(null);
  const [sshError, setSshError] = useState<string | null>(null);
  const [sshBusy, setSshBusy] = useState(false);

  async function handleAssetSshTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedAsset == null) {
      setSshError("请先选择资产。");
      return;
    }
    setSshBusy(true);
    setSshError(null);

    try {
      setSshResult(await runAssetSshTest(selectedAsset.id));
    } catch (error) {
      setSshError(error instanceof Error ? error.message : "SSH test failed");
    } finally {
      setSshBusy(false);
    }
  }

  return (
    <section className="operation-stage-card">
      {stageHeader}
      <p className="operation-stage-description">直接使用当前资产的 SSH 配置和凭据引用做接入预检。</p>
      <form className="control-form" onSubmit={handleAssetSshTest}>
        <AssetSelector
          assets={assets}
          selectedAssetId={selectedAssetId}
          onSelectedAssetChange={onSelectedAssetChange}
        />
        <SelectedAssetSummary asset={selectedAsset} />
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={sshBusy || !canRunAssetSsh}>
            {sshBusy ? "测试中..." : "执行 SSH 测试"}
          </button>
        </div>
      </form>
      {!canRunAssetSsh ? (
        <StatePanel
          tone="info"
          title="当前资产还不能执行 SSH 测试"
          description="需要启用资产、配置用户名，并且保存凭据后才能直接执行。"
        />
      ) : null}
      {sshError ? <StatePanel tone="error" title="SSH 测试失败" description={sshError} /> : null}
      {sshResult ? (
        <ResultCard
          title={sshResult.success ? "连接成功" : "连接失败"}
          tone={sshResult.success ? "good" : "high"}
          summary={sshResult.message}
        />
      ) : null}
    </section>
  );
}
