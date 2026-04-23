"use client";

import { useEffect, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";

import { StatePanel } from "@/components/state-panel";
import type {
  Asset,
  AssetCreatePayload,
  AssetUpdatePayload,
  BaselineRun,
  LinuxInspection,
  PortScanResult,
  SSHTestResult,
  SwitchInspection,
} from "@/lib/api";
import {
  createAsset,
  deleteAsset,
  fetchLinuxInspections,
  fetchSwitchInspections,
  rerunLinuxBaseline,
  rerunSwitchBaseline,
  runAssetBaseline,
  runAssetInspection,
  runAssetPortScan,
  runAssetSshTest,
  updateAsset,
} from "@/lib/api";

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

type PortScanForm = {
  ports: string;
};

type RerunForm = {
  deviceType: "linux" | "switch";
  inspectionId: string;
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

const INITIAL_PORT_SCAN_FORM: PortScanForm = {
  ports: "22,80,443",
};

const INITIAL_RERUN_FORM: RerunForm = {
  deviceType: "linux",
  inspectionId: "",
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

  const [sshResult, setSshResult] = useState<SSHTestResult | null>(null);
  const [sshError, setSshError] = useState<string | null>(null);
  const [sshBusy, setSshBusy] = useState(false);

  const [portScanForm, setPortScanForm] = useState(INITIAL_PORT_SCAN_FORM);
  const [portScanResult, setPortScanResult] = useState<PortScanResult | null>(null);
  const [portScanError, setPortScanError] = useState<string | null>(null);
  const [portScanBusy, setPortScanBusy] = useState(false);

  const [inspectionResult, setInspectionResult] = useState<BaselineRun | null>(null);
  const [inspectionError, setInspectionError] = useState<string | null>(null);
  const [inspectionBusy, setInspectionBusy] = useState(false);

  const [baselineResult, setBaselineResult] = useState<BaselineRun | null>(null);
  const [baselineError, setBaselineError] = useState<string | null>(null);
  const [baselineBusy, setBaselineBusy] = useState(false);

  const [rerunForm, setRerunForm] = useState(INITIAL_RERUN_FORM);
  const [rerunResult, setRerunResult] = useState<BaselineRun | null>(null);
  const [rerunError, setRerunError] = useState<string | null>(null);
  const [rerunBusy, setRerunBusy] = useState(false);

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
        onAssetsChange((current) =>
          current.map((asset) => (asset.id === updated.id ? updated : asset)),
        );
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
                        <span>{asset.connection_type.toUpperCase()} / {asset.port}</span>
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
              sshBusy,
              sshError,
              sshResult,
              handleAssetSshTest,
              portScanForm,
              setPortScanForm,
              portScanBusy,
              portScanError,
              portScanResult,
              handleAssetPortScan,
              inspectionBusy,
              inspectionError,
              inspectionResult,
              handleAssetInspection,
              baselineBusy,
              baselineError,
              baselineResult,
              handleAssetBaseline,
              rerunForm,
              setRerunForm,
              rerunBusy,
              rerunError,
              rerunResult,
              handleBaselineRerun,
            })}
          </div>
        ) : null}
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
  sshBusy: boolean;
  sshError: string | null;
  sshResult: SSHTestResult | null;
  handleAssetSshTest: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  portScanForm: PortScanForm;
  setPortScanForm: Dispatch<SetStateAction<PortScanForm>>;
  portScanBusy: boolean;
  portScanError: string | null;
  portScanResult: PortScanResult | null;
  handleAssetPortScan: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  inspectionBusy: boolean;
  inspectionError: string | null;
  inspectionResult: BaselineRun | null;
  handleAssetInspection: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  baselineBusy: boolean;
  baselineError: string | null;
  baselineResult: BaselineRun | null;
  handleAssetBaseline: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  rerunForm: RerunForm;
  setRerunForm: Dispatch<SetStateAction<RerunForm>>;
  rerunBusy: boolean;
  rerunError: string | null;
  rerunResult: BaselineRun | null;
  handleBaselineRerun: (event: FormEvent<HTMLFormElement>) => Promise<void>;
};

function renderOperationStage(props: RenderOperationStageProps) {
  const activeGroup = OPERATION_GROUPS.find((group) =>
    group.operations.some((operation) => operation.key === props.activeOperation),
  );
  const activeOperationMeta = activeGroup?.operations.find(
    (operation) => operation.key === props.activeOperation,
  );

  if (!activeGroup || !activeOperationMeta) {
    return null;
  }

  const stageHeader = (
    <div className="operation-stage-head">
      <div>
        <span className="operation-stage-kicker">{activeGroup.label}</span>
        <h3>{activeOperationMeta.label}</h3>
      </div>
      <span className="section-meta">{activeGroup.description}</span>
    </div>
  );

  if (props.activeOperation !== "rerun" && props.assets.length === 0) {
    return (
      <section className="operation-stage-card">
        {stageHeader}
        <StatePanel tone="info" title="还没有可执行资产" description="先录入资产并配置连接信息，再从这里直接发起动作。" />
      </section>
    );
  }

  switch (props.activeOperation) {
    case "ssh":
      return (
        <section className="operation-stage-card">
          {stageHeader}
          <p className="operation-stage-description">直接使用当前资产的 SSH 配置和凭据引用做接入预检。</p>
          <form className="control-form" onSubmit={props.handleAssetSshTest}>
            <AssetSelector
              assets={props.assets}
              selectedAssetId={props.selectedAssetId}
              onSelectedAssetChange={props.onSelectedAssetChange}
            />
            <SelectedAssetSummary asset={props.selectedAsset} />
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={props.sshBusy || !props.canRunAssetSsh}>
                {props.sshBusy ? "测试中..." : "执行 SSH 测试"}
              </button>
            </div>
          </form>
          {!props.canRunAssetSsh ? (
            <StatePanel
              tone="info"
              title="当前资产还不能执行 SSH 测试"
              description="需要启用资产、配置用户名，并且保存凭据后才能直接执行。"
            />
          ) : null}
          {props.sshError ? <StatePanel tone="error" title="SSH 测试失败" description={props.sshError} /> : null}
          {props.sshResult ? (
            <ResultCard
              title={props.sshResult.success ? "连接成功" : "连接失败"}
              tone={props.sshResult.success ? "good" : "high"}
              summary={props.sshResult.message}
            />
          ) : null}
        </section>
      );
    case "port_scan":
      return (
        <section className="operation-stage-card">
          {stageHeader}
          <p className="operation-stage-description">直接针对当前资产运行端口扫描，并把扫描记录挂回资产。</p>
          <form className="control-form" onSubmit={props.handleAssetPortScan}>
            <AssetSelector
              assets={props.assets}
              selectedAssetId={props.selectedAssetId}
              onSelectedAssetChange={props.onSelectedAssetChange}
            />
            <SelectedAssetSummary asset={props.selectedAsset} />
            <div className="form-grid">
              <label className="field-stack field-span-2">
                <span className="field-label">扫描端口</span>
                <input
                  className="control-input"
                  value={props.portScanForm.ports}
                  onChange={(event) =>
                    props.setPortScanForm((current) => ({ ...current, ports: event.target.value }))
                  }
                  placeholder="22,80,443"
                />
              </label>
            </div>
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={props.portScanBusy || !props.canRunAssetScan}>
                {props.portScanBusy ? "扫描中..." : "执行端口扫描"}
              </button>
            </div>
          </form>
          {!props.canRunAssetScan ? (
            <StatePanel tone="info" title="当前资产不可执行" description="需要先选择一个启用中的资产。" />
          ) : null}
          {props.portScanError ? <StatePanel tone="error" title="端口扫描失败" description={props.portScanError} /> : null}
          {props.portScanResult ? (
            <ResultCard
              title={`扫描完成: ${props.portScanResult.ip}`}
              tone={props.portScanResult.open_ports.length > 0 ? "medium" : "good"}
              summary={`开放端口 ${props.portScanResult.open_ports.length} 个，检查端口 ${props.portScanResult.checked_ports.join(", ")}`}
              detail={props.portScanResult.message}
            />
          ) : null}
        </section>
      );
    case "inspect":
      return (
        <section className="operation-stage-card">
          {stageHeader}
          <p className="operation-stage-description">根据当前资产类型自动进入 Linux 或交换机巡检，并把最新结果写回资产。</p>
          <form className="control-form" onSubmit={props.handleAssetInspection}>
            <AssetSelector
              assets={props.assets}
              selectedAssetId={props.selectedAssetId}
              onSelectedAssetChange={props.onSelectedAssetChange}
            />
            <SelectedAssetSummary asset={props.selectedAsset} />
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={props.inspectionBusy || !props.canRunAssetSsh}>
                {props.inspectionBusy ? "巡检中..." : "执行资产巡检"}
              </button>
            </div>
          </form>
          {!props.canRunAssetSsh ? (
            <StatePanel tone="info" title="当前资产还不能直接巡检" description="需要启用资产并补齐 SSH 用户名和凭据。" />
          ) : null}
          {props.inspectionError ? <StatePanel tone="error" title="资产巡检失败" description={props.inspectionError} /> : null}
          {props.inspectionResult ? (
            <InspectionCard
              title={`巡检结果 #${props.inspectionResult.inspection_id}`}
              success={props.inspectionResult.success}
              message={props.inspectionResult.message}
              baselineResults={props.inspectionResult.baseline_results}
              vendor={props.inspectionResult.vendor ?? undefined}
            />
          ) : null}
        </section>
      );
    case "baseline":
      return (
        <section className="operation-stage-card">
          {stageHeader}
          <p className="operation-stage-description">基线入口同样围绕当前资产执行，结果会自动落到对应巡检记录上。</p>
          <form className="control-form" onSubmit={props.handleAssetBaseline}>
            <AssetSelector
              assets={props.assets}
              selectedAssetId={props.selectedAssetId}
              onSelectedAssetChange={props.onSelectedAssetChange}
            />
            <SelectedAssetSummary asset={props.selectedAsset} />
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={props.baselineBusy || !props.canRunAssetSsh}>
                {props.baselineBusy ? "执行中..." : "运行基线检查"}
              </button>
            </div>
          </form>
          {!props.canRunAssetSsh ? (
            <StatePanel tone="info" title="当前资产还不能直接跑基线" description="需要启用资产并补齐 SSH 用户名和凭据。" />
          ) : null}
          {props.baselineError ? <StatePanel tone="error" title="基线执行失败" description={props.baselineError} /> : null}
          {props.baselineResult ? (
            <InspectionCard
              title={`基线结果 #${props.baselineResult.inspection_id}`}
              success={props.baselineResult.success}
              message={props.baselineResult.message}
              baselineResults={props.baselineResult.baseline_results}
              vendor={props.baselineResult.vendor ?? undefined}
            />
          ) : null}
        </section>
      );
    case "rerun":
      return (
        <section className="operation-stage-card">
          {stageHeader}
          <p className="operation-stage-description">按巡检记录 ID 单独重跑基线规则，不重新 SSH 登录设备。</p>
          <form className="control-form" onSubmit={props.handleBaselineRerun}>
            <div className="form-grid">
              <label className="field-stack">
                <span className="field-label">设备类型</span>
                <select
                  className="control-select"
                  value={props.rerunForm.deviceType}
                  onChange={(event) =>
                    props.setRerunForm((current) => ({
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
                  value={props.rerunForm.inspectionId}
                  onChange={(event) =>
                    props.setRerunForm((current) => ({ ...current, inspectionId: event.target.value }))
                  }
                  placeholder="12"
                  required
                />
              </label>
            </div>
            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={props.rerunBusy}>
                {props.rerunBusy ? "重跑中..." : "重跑基线"}
              </button>
            </div>
          </form>
          {props.rerunError ? <StatePanel tone="error" title="基线重跑失败" description={props.rerunError} /> : null}
          {props.rerunResult ? (
            <InspectionCard
              title={`重跑结果 #${props.rerunResult.inspection_id}`}
              success={props.rerunResult.success}
              message={props.rerunResult.message}
              baselineResults={props.rerunResult.baseline_results}
              vendor={props.rerunResult.vendor ?? undefined}
            />
          ) : null}
        </section>
      );
    default:
      return null;
  }
}

function AssetSelector({
  assets,
  selectedAssetId,
  onSelectedAssetChange,
}: {
  assets: Asset[];
  selectedAssetId: number | null;
  onSelectedAssetChange: (assetId: number | null) => void;
}) {
  return (
    <div className="form-grid">
      <label className="field-stack field-span-2">
        <span className="field-label">当前资产</span>
        <select
          className="control-select"
          value={selectedAssetId ?? ""}
          onChange={(event) => onSelectedAssetChange(event.target.value ? Number(event.target.value) : null)}
        >
          <option value="">请选择资产</option>
          {assets.map((asset) => (
            <option key={asset.id} value={asset.id}>
              {asset.name} / {asset.ip} / {asset.type.toUpperCase()}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function SelectedAssetSummary({ asset }: { asset: Asset | null }) {
  if (asset == null) {
    return null;
  }

  return (
    <article className="metric-card tone-neutral">
      <div className="metric-label">当前执行对象</div>
      <div className="metric-value" style={{ fontSize: "1.2rem" }}>
        {asset.name}
      </div>
      <p className="metric-hint">
        {asset.ip} / {asset.type.toUpperCase()} / {asset.connection_type.toUpperCase()}:{asset.port}
      </p>
      <p className="metric-hint">
        {asset.is_enabled ? "已启用" : "已停用"} / {asset.username ?? "无用户名"} / {asset.credential_configured ? "凭据已配置" : "凭据缺失"}
      </p>
    </article>
  );
}

function ResultCard({
  title,
  summary,
  detail,
  tone,
}: {
  title: string;
  summary: string;
  detail?: string;
  tone: "good" | "medium" | "high" | "neutral";
}) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <div className="metric-label">{title}</div>
      <div className="metric-value" style={{ fontSize: "1.55rem" }}>
        {summary}
      </div>
      {detail ? <p className="metric-hint">{detail}</p> : null}
    </article>
  );
}

function InspectionCard({
  title,
  success,
  message,
  baselineResults,
  vendor,
}: {
  title: string;
  success: boolean;
  message: string;
  baselineResults: BaselineRun["baseline_results"];
  vendor?: string;
}) {
  const failCount = baselineResults.filter((item) => item.status === "fail").length;
  const unknownCount = baselineResults.filter((item) => item.status === "unknown").length;
  const notApplicableCount = baselineResults.filter((item) => item.status === "not_applicable").length;

  return (
    <div className="result-stack">
      <ResultCard
        title={vendor ? `${title} / ${vendor}` : title}
        tone={success ? (failCount > 0 ? "medium" : "good") : "high"}
        summary={message}
        detail={`失败项 ${failCount}，待补核 ${unknownCount}，不适用 ${notApplicableCount}，总规则 ${baselineResults.length}`}
      />
      {baselineResults.length > 0 ? (
        <div className="list-stack">
          {baselineResults.slice(0, 3).map((item) => (
            <article key={item.rule_id} className="list-item">
              <div className="list-item-main">
                <h4 className="list-item-title">{item.rule_name}</h4>
                <p className="list-item-copy">{item.detail}</p>
                <p className="list-item-copy">{item.evidence}</p>
              </div>
              <div className="list-item-meta">
                <span
                  className={`status-chip tone-${item.status === "fail" ? "high" : item.status === "pass" ? "good" : "neutral"}`}
                >
                  {item.status}
                </span>
                <span className="status-chip tone-neutral">{item.risk_level}</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
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

function parsePorts(value: string): number[] {
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((port) => Number.isInteger(port) && port > 0);
}
