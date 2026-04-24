"use client";

import { useEffect, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";

import { StatePanel } from "@/components/state-panel";
import type { Asset, AssetCreatePayload, AssetUpdatePayload, LinuxInspection, SwitchInspection } from "@/lib/api";
import { createAsset, deleteAsset, updateAsset } from "@/lib/api";

import { BaselineRunPanel } from "./baseline-run-panel";
import { LinuxInspectionPanel } from "./linux-inspection-panel";
import { EmptyAssetStage, OperationStageHeader } from "./operation-panel-shared";
import { PortScanPanel } from "./port-scan-panel";
import { ScheduledTasksPanel } from "../scheduled-tasks/scheduled-tasks-panel";
import { SshTestPanel } from "./ssh-test-panel";
import { SwitchInspectionPanel } from "./switch-inspection-panel";

type AssetConsoleAction = "edit" | "ssh" | "port_scan" | "inspect" | "baseline";

type AssetActionRequest = {
  assetId: number;
  action: AssetConsoleAction;
  nonce: number;
};

type OperationsConsoleProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  actionRequest: AssetActionRequest | null;
  onSelectedAssetChange: (assetId: number | null) => void;
  onAssetsChange: Dispatch<SetStateAction<Asset[]>>;
  onLinuxInspectionsChange: Dispatch<SetStateAction<LinuxInspection[]>>;
  onSwitchInspectionsChange: Dispatch<SetStateAction<SwitchInspection[]>>;
};

type AssetFormState = {
  ip: string;
  type: "linux" | "switch";
  name: string;
  connection_type: string;
  port: string;
  username: string;
  vendor: string;
  credential_password: string;
  is_enabled: boolean;
};

type OperationKey = "ssh" | "port_scan" | "inspect" | "baseline" | "rerun";

const INITIAL_ASSET_FORM: AssetFormState = {
  ip: "",
  type: "linux",
  name: "",
  connection_type: "ssh",
  port: "22",
  username: "",
  vendor: "h3c",
  credential_password: "",
  is_enabled: true,
};

const OPERATION_GROUPS: Array<{
  key: string;
  label: string;
  description: string;
  operations: Array<{ key: OperationKey; label: string }>;
}> = [
  {
    key: "prep",
    label: "接入预检",
    description: "基于当前资产直接验证 SSH 和端口暴露面。",
    operations: [
      { key: "ssh", label: "SSH 测试" },
      { key: "port_scan", label: "端口扫描" },
    ],
  },
  {
    key: "inspect",
    label: "执行闭环",
    description: "巡检和基线都以当前资产为主入口，结果自动回挂资产。",
    operations: [
      { key: "inspect", label: "资产巡检" },
      { key: "baseline", label: "基线检查" },
    ],
  },
  {
    key: "baseline",
    label: "规则复核",
    description: "对已有巡检记录单独重跑基线规则，不重新登录设备。",
    operations: [{ key: "rerun", label: "基线重跑" }],
  },
];

export function OperationsConsole({
  assets,
  selectedAssetId,
  actionRequest,
  onSelectedAssetChange,
  onAssetsChange,
  onLinuxInspectionsChange,
  onSwitchInspectionsChange,
}: OperationsConsoleProps) {
  const [assetForm, setAssetForm] = useState(INITIAL_ASSET_FORM);
  const [editingAssetId, setEditingAssetId] = useState<number | null>(null);
  const [assetMessage, setAssetMessage] = useState<string | null>(null);
  const [assetError, setAssetError] = useState<string | null>(null);
  const [assetBusy, setAssetBusy] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeOperation, setActiveOperation] = useState<OperationKey>("ssh");

  const selectedAsset = assets.find((asset) => asset.id === selectedAssetId) ?? null;
  const canRunAssetSsh =
    selectedAsset != null &&
    selectedAsset.is_enabled &&
    selectedAsset.connection_type === "ssh" &&
    selectedAsset.credential_configured &&
    Boolean(selectedAsset.username);
  const canRunAssetScan = selectedAsset != null && selectedAsset.is_enabled;

  useEffect(() => {
    if (actionRequest == null) {
      return;
    }

    const targetAsset = assets.find((asset) => asset.id === actionRequest.assetId);
    if (targetAsset == null) {
      return;
    }

    if (actionRequest.action === "edit") {
      startAssetEdit(targetAsset);
      return;
    }

    setEditingAssetId(null);
    setAssetForm(INITIAL_ASSET_FORM);
    setAssetError(null);
    setAssetMessage(null);
    setAdvancedOpen(true);
    setActiveOperation(actionRequest.action);
  }, [actionRequest, assets]);

  function startAssetEdit(asset: Asset) {
    onSelectedAssetChange(asset.id);
    setEditingAssetId(asset.id);
    setAssetForm(buildAssetFormFromAsset(asset));
    setAssetError(null);
    setAssetMessage(`已载入 ${asset.name} 的接入配置，可直接修改用户名或密码。`);
  }

  function resetAssetEditor() {
    setEditingAssetId(null);
    setAssetForm(INITIAL_ASSET_FORM);
    setAssetError(null);
    setAssetMessage(null);
  }

  async function handleAssetSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAssetBusy(true);
    setAssetError(null);
    setAssetMessage(null);

    try {
      if (editingAssetId == null) {
        const created = await createAsset(buildAssetPayload(assetForm));
        onAssetsChange((current) => [created, ...current]);
        onSelectedAssetChange(created.id);
        setAssetForm(INITIAL_ASSET_FORM);
        setAssetMessage(`已创建资产 ${created.name} (${created.ip})。`);
      } else {
        const updated = await updateAsset(editingAssetId, buildAssetUpdatePayload(assetForm));
        onAssetsChange((current) => current.map((asset) => (asset.id === updated.id ? updated : asset)));
        onSelectedAssetChange(updated.id);
        setEditingAssetId(updated.id);
        setAssetForm(buildAssetFormFromAsset(updated));
        setAssetMessage(`已更新资产 ${updated.name} 的接入配置。`);
      }
    } catch (error) {
      setAssetError(error instanceof Error ? error.message : "Asset save failed");
    } finally {
      setAssetBusy(false);
    }
  }

  async function handleAssetDelete(assetId: number) {
    setAssetBusy(true);
    setAssetError(null);
    setAssetMessage(null);

    try {
      await deleteAsset(assetId);
      const remainingAssets = assets.filter((item) => item.id !== assetId);
      onAssetsChange(remainingAssets);
      if (editingAssetId === assetId) {
        resetAssetEditor();
      }
      if (selectedAssetId === assetId) {
        onSelectedAssetChange(remainingAssets[0]?.id ?? null);
      }
      setAssetMessage(`已删除资产 ID ${assetId}。`);
    } catch (error) {
      setAssetError(error instanceof Error ? error.message : "Asset deletion failed");
    } finally {
      setAssetBusy(false);
    }
  }

  return (
    <>
      <section id="asset-management-section" className="section-card asset-management-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">{editingAssetId == null ? "资产管理" : "编辑资产接入"}</h3>
            <p className="section-description">
              {editingAssetId == null
                ? "资产录入时同时补齐连接元数据和凭据引用，后续执行动作直接围绕资产进行。"
                : "当前模式用于修改既有资产的用户名、密码和接入参数，密码留空则保持原值。"}
            </p>
          </div>
          <div className="section-meta">
            {editingAssetId == null ? `当前 ${assets.length} 台` : `编辑 ID ${editingAssetId}`}
          </div>
        </div>

        <div className="section-layout">
          <form className="control-form" onSubmit={handleAssetSubmit}>
            <div className="form-grid">
              <label className="field-stack">
                <span className="field-label">资产名称</span>
                <input
                  className="control-input"
                  value={assetForm.name}
                  onChange={(event) => setAssetForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="prod-web-01"
                  required
                />
              </label>
              <label className="field-stack">
                <span className="field-label">IP 地址</span>
                <input
                  className="control-input"
                  value={assetForm.ip}
                  onChange={(event) => setAssetForm((current) => ({ ...current, ip: event.target.value }))}
                  placeholder="192.168.1.10"
                  required
                  disabled={editingAssetId != null}
                />
              </label>
              <label className="field-stack">
                <span className="field-label">资产类型</span>
                <select
                  className="control-select"
                  value={assetForm.type}
                  onChange={(event) =>
                    setAssetForm((current) => ({
                      ...current,
                      type: event.target.value as "linux" | "switch",
                      vendor: event.target.value === "switch" ? current.vendor || "h3c" : "",
                    }))
                  }
                  disabled={editingAssetId != null}
                >
                  <option value="linux">Linux</option>
                  <option value="switch">Switch</option>
                </select>
              </label>
              <label className="field-stack">
                <span className="field-label">连接端口</span>
                <input
                  className="control-input"
                  value={assetForm.port}
                  onChange={(event) => setAssetForm((current) => ({ ...current, port: event.target.value }))}
                  placeholder="22"
                  required
                />
              </label>
              <label className="field-stack">
                <span className="field-label">用户名</span>
                <input
                  className="control-input"
                  value={assetForm.username}
                  onChange={(event) => setAssetForm((current) => ({ ...current, username: event.target.value }))}
                  placeholder={assetForm.type === "switch" ? "admin" : "root"}
                />
              </label>
              <label className="field-stack">
                <span className="field-label">接入密码</span>
                <input
                  className="control-input"
                  type="password"
                  value={assetForm.credential_password}
                  onChange={(event) =>
                    setAssetForm((current) => ({ ...current, credential_password: event.target.value }))
                  }
                  placeholder={editingAssetId == null ? "******" : "留空表示保持原密码"}
                />
              </label>
              {assetForm.type === "switch" ? (
                <label className="field-stack">
                  <span className="field-label">厂商</span>
                  <select
                    className="control-select"
                    value={assetForm.vendor}
                    onChange={(event) => setAssetForm((current) => ({ ...current, vendor: event.target.value }))}
                  >
                    <option value="h3c">H3C</option>
                  </select>
                </label>
              ) : null}
              <label className="field-stack">
                <span className="field-label">执行状态</span>
                <select
                  className="control-select"
                  value={assetForm.is_enabled ? "enabled" : "disabled"}
                  onChange={(event) =>
                    setAssetForm((current) => ({
                      ...current,
                      is_enabled: event.target.value === "enabled",
                    }))
                  }
                >
                  <option value="enabled">启用</option>
                  <option value="disabled">停用</option>
                </select>
              </label>
            </div>
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={assetBusy}>
                {assetBusy ? "提交中..." : editingAssetId == null ? "新增资产" : "保存修改"}
              </button>
              {editingAssetId != null ? (
                <button className="secondary-button" type="button" onClick={resetAssetEditor} disabled={assetBusy}>
                  取消编辑
                </button>
              ) : null}
              {assetMessage ? <span className="status-chip tone-good">{assetMessage}</span> : null}
            </div>
          </form>

          {assetError ? <StatePanel tone="error" title="资产操作失败" description={assetError} /> : null}

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>IP</th>
                  <th>接入</th>
                  <th>选择 / 编辑</th>
                  <th>删除</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id}>
                    <td>
                      <div className="cell-primary">
                        <span>{asset.name}</span>
                        <span>{asset.type.toUpperCase()}</span>
                      </div>
                    </td>
                    <td className="mono">{asset.ip}</td>
                    <td>
                      <div className="cell-primary">
                        <span>
                          {asset.connection_type.toUpperCase()} / {asset.port}
                        </span>
                        <span>{asset.credential_configured ? "凭据已配置" : "凭据缺失"}</span>
                      </div>
                    </td>
                    <td>
                      <div className="row-action-group">
                        <button
                          className="secondary-button"
                          type="button"
                          onClick={() => startAssetEdit(asset)}
                          disabled={assetBusy}
                        >
                          编辑接入
                        </button>
                        <button
                          className={selectedAssetId === asset.id ? "secondary-button" : "primary-button"}
                          type="button"
                          onClick={() => onSelectedAssetChange(asset.id)}
                        >
                          {selectedAssetId === asset.id ? "当前资产" : "设为当前"}
                        </button>
                      </div>
                    </td>
                    <td>
                      <button
                        className="danger-button"
                        type="button"
                        onClick={() => handleAssetDelete(asset.id)}
                        disabled={assetBusy}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
                {assets.length === 0 ? (
                  <tr>
                    <td colSpan={5}>当前没有资产，请先创建。</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section id="asset-execution-section" className="advanced-operations-shell">
        <div className="advanced-operations-summary">
          <div className="advanced-operations-copy">
            <span className="advanced-operations-kicker">高级操作</span>
            <h3>执行台</h3>
            <p>当前执行台默认围绕选中资产工作，只有基线重跑仍保留按巡检 ID 触发。</p>
          </div>
          <div className="advanced-operations-actions">
            <span className="status-chip tone-neutral">5 类动作</span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setAdvancedOpen((current) => !current)}
              aria-expanded={advancedOpen}
            >
              {advancedOpen ? "收起高级操作" : "展开高级操作"}
            </button>
          </div>
        </div>

        {advancedOpen ? (
          <div className="advanced-operations-body">
            <div className="operation-lane-list" aria-label="执行台分组">
              {OPERATION_GROUPS.map((group) => (
                <section key={group.key} className="operation-lane">
                  <div className="operation-lane-head">
                    <strong>{group.label}</strong>
                    <p>{group.description}</p>
                  </div>
                  <div className="operation-chip-row">
                    {group.operations.map((operation) => (
                      <button
                        key={operation.key}
                        className={`operation-chip${operation.key === activeOperation ? " is-active" : ""}`}
                        type="button"
                        onClick={() => setActiveOperation(operation.key)}
                      >
                        {operation.label}
                      </button>
                    ))}
                  </div>
                </section>
              ))}
            </div>

            {renderOperationStage({
              assets,
              selectedAssetId,
              onSelectedAssetChange,
              selectedAsset,
              canRunAssetSsh,
              canRunAssetScan,
              activeOperation,
              onLinuxInspectionsChange,
              onSwitchInspectionsChange,
            })}
          </div>
        ) : null}
      </section>

      <section className="section-card">
        <div className="section-header">
          <div>
            <h3 className="section-title">调度任务</h3>
            <p className="section-description">管理定时调度任务，支持立即触发、启用/禁用和编辑删除。</p>
          </div>
        </div>
        <ScheduledTasksPanel assets={assets} />
      </section>
    </>
  );
}

type RenderOperationStageProps = {
  assets: Asset[];
  selectedAssetId: number | null;
  onSelectedAssetChange: (assetId: number | null) => void;
  selectedAsset: Asset | null;
  canRunAssetSsh: boolean;
  canRunAssetScan: boolean;
  activeOperation: OperationKey;
  onLinuxInspectionsChange: Dispatch<SetStateAction<LinuxInspection[]>>;
  onSwitchInspectionsChange: Dispatch<SetStateAction<SwitchInspection[]>>;
};

function renderOperationStage(props: RenderOperationStageProps) {
  const activeGroup = OPERATION_GROUPS.find((group) =>
    group.operations.some((operation) => operation.key === props.activeOperation),
  );
  const activeOperationMeta = activeGroup?.operations.find((operation) => operation.key === props.activeOperation);

  if (!activeGroup || !activeOperationMeta) {
    return null;
  }

  const stageHeader = (
    <OperationStageHeader
      groupLabel={activeGroup.label}
      operationLabel={activeOperationMeta.label}
      description={activeGroup.description}
    />
  );

  if (props.activeOperation !== "rerun" && props.assets.length === 0) {
    return <EmptyAssetStage stageHeader={stageHeader} />;
  }

  switch (props.activeOperation) {
    case "ssh":
      return (
        <SshTestPanel
          assets={props.assets}
          selectedAssetId={props.selectedAssetId}
          selectedAsset={props.selectedAsset}
          canRunAssetSsh={props.canRunAssetSsh}
          onSelectedAssetChange={props.onSelectedAssetChange}
          stageHeader={stageHeader}
        />
      );
    case "port_scan":
      return (
        <PortScanPanel
          assets={props.assets}
          selectedAssetId={props.selectedAssetId}
          selectedAsset={props.selectedAsset}
          canRunAssetScan={props.canRunAssetScan}
          onSelectedAssetChange={props.onSelectedAssetChange}
          stageHeader={stageHeader}
        />
      );
    case "inspect": {
      const InspectionPanel = props.selectedAsset?.type === "switch" ? SwitchInspectionPanel : LinuxInspectionPanel;

      return (
        <InspectionPanel
          assets={props.assets}
          selectedAssetId={props.selectedAssetId}
          selectedAsset={props.selectedAsset}
          canRunAssetSsh={props.canRunAssetSsh}
          onSelectedAssetChange={props.onSelectedAssetChange}
          onLinuxInspectionsChange={props.onLinuxInspectionsChange}
          onSwitchInspectionsChange={props.onSwitchInspectionsChange}
          stageHeader={stageHeader}
        />
      );
    }
    case "baseline":
      return (
        <BaselineRunPanel
          assets={props.assets}
          selectedAssetId={props.selectedAssetId}
          selectedAsset={props.selectedAsset}
          canRunAssetSsh={props.canRunAssetSsh}
          onSelectedAssetChange={props.onSelectedAssetChange}
          onLinuxInspectionsChange={props.onLinuxInspectionsChange}
          onSwitchInspectionsChange={props.onSwitchInspectionsChange}
          stageHeader={stageHeader}
        />
      );
    case "rerun":
      return (
        <BaselineRunPanel
          assets={props.assets}
          selectedAssetId={props.selectedAssetId}
          selectedAsset={props.selectedAsset}
          canRunAssetSsh={props.canRunAssetSsh}
          onSelectedAssetChange={props.onSelectedAssetChange}
          onLinuxInspectionsChange={props.onLinuxInspectionsChange}
          onSwitchInspectionsChange={props.onSwitchInspectionsChange}
          stageHeader={stageHeader}
          mode="rerun"
        />
      );
    default:
      return null;
  }
}

function buildAssetPayload(form: AssetFormState): AssetCreatePayload {
  const payload: AssetCreatePayload = {
    ip: form.ip,
    type: form.type,
    name: form.name,
    connection_type: form.connection_type,
    port: Number(form.port) || 22,
    username: form.username.trim() || null,
    vendor: form.type === "switch" ? form.vendor.trim() || null : null,
    is_enabled: form.is_enabled,
  };

  const credentialPassword = form.credential_password.trim();
  if (credentialPassword.length > 0) {
    payload.credential_password = credentialPassword;
  }

  return payload;
}

function buildAssetUpdatePayload(form: AssetFormState): AssetUpdatePayload {
  const payload: AssetUpdatePayload = {
    name: form.name.trim(),
    connection_type: form.connection_type,
    port: Number(form.port) || 22,
    username: form.username.trim() || null,
    vendor: form.type === "switch" ? form.vendor.trim() || null : null,
    is_enabled: form.is_enabled,
  };

  const credentialPassword = form.credential_password.trim();
  if (credentialPassword.length > 0) {
    payload.credential_password = credentialPassword;
  }

  return payload;
}

function buildAssetFormFromAsset(asset: Asset): AssetFormState {
  return {
    ip: asset.ip,
    type: asset.type === "switch" ? "switch" : "linux",
    name: asset.name,
    connection_type: asset.connection_type,
    port: String(asset.port),
    username: asset.username ?? "",
    vendor: asset.vendor ?? "h3c",
    credential_password: "",
    is_enabled: asset.is_enabled,
  };
}
