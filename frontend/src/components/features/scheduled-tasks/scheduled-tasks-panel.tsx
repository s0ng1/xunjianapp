"use client";

import { useCallback, useEffect, useState } from "react";
import type { Asset } from "@/lib/api";
import {
  createScheduledTask,
  deleteScheduledTask,
  listScheduledTasks,
  triggerScheduledTask,
  type ScheduledTask,
  type ScheduledTaskCreate,
  type ScheduleType,
  type TaskType,
  updateScheduledTask,
} from "@/lib/api/scheduled-tasks";
import { StatePanel } from "@/components/state-panel";

type FilterStatus = "all" | "enabled" | "disabled";

const TASK_TYPE_LABELS: Record<TaskType, string> = {
  ssh_test: "SSH 测试",
  linux_inspection: "Linux 巡检",
  switch_inspection: "交换机巡检",
  port_scan: "端口扫描",
  baseline_check: "基线检查",
};

const SCHEDULE_TYPE_LABELS: Record<ScheduleType, string> = {
  interval: "间隔执行",
  cron: "Cron 表达式",
};

const INITIAL_FORM: Omit<ScheduledTaskCreate, "schedule_type"> & {
  schedule_type: ScheduleType;
  asset_id: number | null;
} = {
  name: "",
  task_type: "linux_inspection",
  asset_id: null,
  schedule_type: "interval",
  interval_seconds: 3600,
  cron_expression: "",
  timezone: "Asia/Shanghai",
  params: {},
  is_enabled: true,
};

export function ScheduledTasksPanel({ assets }: { assets: Asset[] }) {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [form, setForm] = useState(INITIAL_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const [filterStatus, setFilterStatus] = useState<FilterStatus>("all");
  const [filterType, setFilterType] = useState<TaskType | "">("");
  const [showForm, setShowForm] = useState(false);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: { task_type?: TaskType; is_enabled?: boolean } = {};
      if (filterType) filters.task_type = filterType as TaskType;
      if (filterStatus === "enabled") filters.is_enabled = true;
      else if (filterStatus === "disabled") filters.is_enabled = false;
      const data = await listScheduledTasks(filters);
      setTasks(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载任务失败");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterType]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);

    const payload: ScheduledTaskCreate = {
      name: form.name,
      task_type: form.task_type,
      asset_id: form.asset_id,
      schedule_type: form.schedule_type,
      interval_seconds: form.schedule_type === "interval" ? form.interval_seconds : null,
      cron_expression: form.schedule_type === "cron" ? form.cron_expression : null,
      timezone: form.timezone,
      params: form.params,
      is_enabled: form.is_enabled,
    };

    try {
      if (editingId == null) {
        const created = await createScheduledTask(payload);
        setTasks((prev) => [created, ...prev]);
        setMessage(`任务 "${created.name}" 创建成功`);
      } else {
        const updated = await updateScheduledTask(editingId, payload);
        setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
        setMessage(`任务 "${updated.name}" 更新成功`);
      }
      resetForm();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(taskId: number) {
    if (!confirm("确定要删除这个任务吗？")) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await deleteScheduledTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setMessage("任务已删除");
      if (editingId === taskId) resetForm();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleEnabled(task: ScheduledTask) {
    try {
      const updated = await updateScheduledTask(task.id, { is_enabled: !task.is_enabled });
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "切换状态失败");
    }
  }

  async function handleTrigger(taskId: number) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await triggerScheduledTask(taskId);
      setMessage(result.message || "触发成功");
      await loadTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "触发失败");
    } finally {
      setBusy(false);
    }
  }

  function startEdit(task: ScheduledTask) {
    setEditingId(task.id);
    setForm({
      name: task.name,
      task_type: task.task_type,
      asset_id: task.asset_id,
      schedule_type: task.schedule_type,
      interval_seconds: task.interval_seconds ?? 3600,
      cron_expression: task.cron_expression ?? "",
      timezone: task.timezone,
      params: task.params,
      is_enabled: task.is_enabled,
    });
    setShowForm(true);
    setError(null);
    setMessage(null);
  }

  function resetForm() {
    setForm(INITIAL_FORM);
    setEditingId(null);
    setShowForm(false);
    setError(null);
    setMessage(null);
  }

  const filteredTasks = tasks;

  return (
    <section className="operation-stage-card">
      <div className="operation-stage-head">
        <div>
          <span className="operation-stage-kicker">调度管理</span>
          <h3>调度任务</h3>
        </div>
        <span className="section-meta">{filteredTasks.length} 个任务</span>
      </div>

      <div className="filter-row">
        <div className="filter-group">
          <span className="filter-label">状态</span>
          <select
            className="control-select filter-select"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
          >
            <option value="all">全部</option>
            <option value="enabled">已启用</option>
            <option value="disabled">已禁用</option>
          </select>
        </div>
        <div className="filter-group">
          <span className="filter-label">类型</span>
          <select
            className="control-select filter-select"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as TaskType | "")}
          >
            <option value="">全部</option>
            {(Object.keys(TASK_TYPE_LABELS) as TaskType[]).map((t) => (
              <option key={t} value={t}>
                {TASK_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <button
          className={showForm ? "secondary-button" : "primary-button"}
          type="button"
          onClick={() => {
            if (showForm && editingId == null) {
              resetForm();
            } else {
              setShowForm((v) => !v);
            }
          }}
        >
          {showForm ? (editingId == null ? "取消" : "取消") : "+ 新建任务"}
        </button>
      </div>

      {showForm ? (
        <form className="control-form task-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label className="field-stack">
              <span className="field-label">任务名称</span>
              <input
                className="control-input"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="每日 Linux 巡检"
                required
              />
            </label>
            <label className="field-stack">
              <span className="field-label">任务类型</span>
              <select
                className="control-select"
                value={form.task_type}
                onChange={(e) => setForm((f) => ({ ...f, task_type: e.target.value as TaskType }))}
              >
                {(Object.keys(TASK_TYPE_LABELS) as TaskType[]).map((t) => (
                  <option key={t} value={t}>
                    {TASK_TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-stack">
              <span className="field-label">关联资产</span>
              <select
                className="control-select"
                value={form.asset_id ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, asset_id: e.target.value ? Number(e.target.value) : null }))
                }
              >
                <option value="">不关联</option>
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} / {a.ip}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-stack">
              <span className="field-label">调度类型</span>
              <select
                className="control-select"
                value={form.schedule_type}
                onChange={(e) => setForm((f) => ({ ...f, schedule_type: e.target.value as ScheduleType }))}
              >
                {(Object.keys(SCHEDULE_TYPE_LABELS) as ScheduleType[]).map((s) => (
                  <option key={s} value={s}>
                    {SCHEDULE_TYPE_LABELS[s]}
                  </option>
                ))}
              </select>
            </label>
            {form.schedule_type === "interval" ? (
              <label className="field-stack">
                <span className="field-label">间隔（秒）</span>
                <input
                  className="control-input"
                  type="number"
                  min={60}
                  value={form.interval_seconds ?? 3600}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, interval_seconds: Number(e.target.value) }))
                  }
                  required
                />
              </label>
            ) : (
              <label className="field-stack">
                <span className="field-label">Cron 表达式</span>
                <input
                  className="control-input"
                  value={form.cron_expression ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, cron_expression: e.target.value }))}
                  placeholder="0 3 * * *"
                  required
                />
              </label>
            )}
            <label className="field-stack">
              <span className="field-label">时区</span>
              <input
                className="control-input"
                value={form.timezone}
                onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
                placeholder="Asia/Shanghai"
              />
            </label>
            <label className="field-stack">
              <span className="field-label">执行状态</span>
              <select
                className="control-select"
                value={form.is_enabled ? "enabled" : "disabled"}
                onChange={(e) => setForm((f) => ({ ...f, is_enabled: e.target.value === "enabled" }))}
              >
                <option value="enabled">启用</option>
                <option value="disabled">停用</option>
              </select>
            </label>
          </div>
          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "保存中..." : editingId == null ? "创建任务" : "保存修改"}
            </button>
            {editingId != null && (
              <button className="secondary-button" type="button" onClick={resetForm} disabled={busy}>
                取消
              </button>
            )}
          </div>
        </form>
      ) : null}

      {error ? <StatePanel tone="error" title="操作失败" description={error} /> : null}
      {message ? <StatePanel tone="info" title="提示" description={message} /> : null}

      {loading ? (
        <p className="loading-hint">加载中...</p>
      ) : filteredTasks.length === 0 ? (
        <StatePanel
          tone="info"
          title="暂无任务"
          description="点击上方「新建任务」创建一个调度任务"
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>类型</th>
                <th>调度方式</th>
                <th>下次执行</th>
                <th>状态</th>
                <th>启用</th>
                <th>最后执行</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredTasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <div className="cell-primary">
                      <span className="cell-title">{task.name}</span>
                      {task.asset_id != null ? (
                        <span className="cell-sub">
                          {assets.find((a) => a.id === task.asset_id)?.name ?? `资产 #${task.asset_id}`}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td>{TASK_TYPE_LABELS[task.task_type] ?? task.task_type}</td>
                  <td>
                    <div className="cell-primary">
                      <span>{SCHEDULE_TYPE_LABELS[task.schedule_type]}</span>
                      <span className="cell-sub">
                        {task.schedule_type === "interval"
                          ? `${task.interval_seconds} 秒`
                          : task.cron_expression}
                      </span>
                    </div>
                  </td>
                  <td className="mono">
                    {task.next_run_at ? new Date(task.next_run_at).toLocaleString("zh-CN") : "—"}
                  </td>
                  <td>
                    {task.last_status ? (
                      <span
                        className={`status-chip ${
                          task.last_status === "success"
                            ? "tone-good"
                            : task.last_status === "failed"
                            ? "tone-bad"
                            : "tone-neutral"
                        }`}
                      >
                        {task.last_status}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={task.is_enabled}
                        onChange={() => handleToggleEnabled(task)}
                        disabled={busy}
                      />
                      <span className="toggle-slider" />
                    </label>
                  </td>
                  <td>
                    {task.last_run_at ? (
                      <div className="cell-primary">
                        <span className="cell-sub">{new Date(task.last_run_at).toLocaleString("zh-CN")}</span>
                        {task.last_message ? (
                          <span className="cell-sub text-overflow-ellipsis" title={task.last_message}>
                            {task.last_message}
                          </span>
                        ) : null}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <div className="row-action-group">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => handleTrigger(task.id)}
                        disabled={busy}
                        title="立即触发"
                      >
                        触发
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => startEdit(task)}
                        disabled={busy}
                      >
                        编辑
                      </button>
                      <button
                        className="danger-button"
                        type="button"
                        onClick={() => handleDelete(task.id)}
                        disabled={busy}
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
