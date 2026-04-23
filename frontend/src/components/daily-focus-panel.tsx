"use client";

import { useState } from "react";

import { FocusRiskOverview, type FocusRiskOverviewData } from "@/components/focus-risk-overview";
import { StatePanel } from "@/components/state-panel";
import {
  fetchDailyFocus,
  updateDailyFocusItemState,
  type DailyFocus,
  type DailyFocusItem,
  type DailyFocusItemStatus,
  type DailyFocusPriorityDevice,
} from "@/lib/api";
import { formatDateTime } from "@/lib/inspection-view";

type DailyFocusPanelProps = {
  focus: DailyFocus;
  overview: FocusRiskOverviewData;
};

type ItemDraft = {
  status: DailyFocusItemStatus;
  remark: string;
};

type ItemMessage = {
  tone: "error" | "info";
  text: string;
};

const STATUS_OPTIONS: Array<{ value: DailyFocusItemStatus; label: string }> = [
  { value: "pending", label: "未处理" },
  { value: "in_progress", label: "处理中" },
  { value: "resolved", label: "已处理" },
  { value: "ignored", label: "已忽略" },
  { value: "needs_manual_confirmation", label: "需人工确认" },
];

export function DailyFocusPanel({ focus, overview }: DailyFocusPanelProps) {
  const [focusState, setFocusState] = useState(focus);
  const [drafts, setDrafts] = useState<Record<string, ItemDraft>>(() => buildDraftMap(focus));
  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Record<string, ItemMessage>>({});

  const syncFocus = (nextFocus: DailyFocus) => {
    setFocusState(nextFocus);
    setDrafts(buildDraftMap(nextFocus));
  };

  const updateDraft = (itemId: string, patch: Partial<ItemDraft>) => {
    setDrafts((current) => ({
      ...current,
      [itemId]: {
        ...(current[itemId] ?? { status: "pending", remark: "" }),
        ...patch,
      },
    }));
    setMessages((current) => {
      if (!(itemId in current)) {
        return current;
      }
      const next = { ...current };
      delete next[itemId];
      return next;
    });
  };

  const handleSave = async (item: DailyFocusItem) => {
    const draft = drafts[item.id] ?? {
      status: item.status,
      remark: item.remark ?? "",
    };
    setSavingItemId(item.id);
    setMessages((current) => {
      const next = { ...current };
      delete next[item.id];
      return next;
    });

    try {
      await updateDailyFocusItemState(item.id, {
        reference_date: focusState.reference_date,
        status: draft.status,
        remark: draft.remark,
        updated_by: "local-operator",
      });
      const nextFocus = await fetchDailyFocus(focusState.reference_date);
      syncFocus(nextFocus);
      setMessages((current) => ({
        ...current,
        [item.id]: { tone: "info", text: "状态已保存" },
      }));
    } catch (error) {
      const text = error instanceof Error ? error.message : "保存失败";
      setMessages((current) => ({
        ...current,
        [item.id]: { tone: "error", text },
      }));
    } finally {
      setSavingItemId(null);
    }
  };

  return (
    <div className="page-stack daily-focus-board">
      <section className="panel-card priority-panel">
        <div className="section-head">
          <div>
            <h3>今日必须处理</h3>
            <p>只保留当前最新巡检中仍未闭环的高危项。</p>
          </div>
          <div className="section-meta">共 {focusState.summary.must_handle_count} 项</div>
        </div>

        {focusState.today_must_handle.length > 0 ? (
          <div className="focus-group-grid">
            {focusState.today_must_handle.map((group) => (
              <article key={`${group.asset_ip}-${group.asset_name}`} className="focus-group-card">
                <div className="headline-row">
                  <strong>{group.asset_name}</strong>
                  <span className="badge tone-critical">{group.asset_ip}</span>
                </div>
                <div className="focus-item-list">
                  {group.items.map((item) => renderFocusItem(item, drafts, messages, savingItemId, updateDraft, handleSave))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <StatePanel
            tone="empty"
            title="今天没有必须立刻处理的高危项"
            description="当前最新巡检结果中没有检出高危 fail，或者还没有 Linux 巡检数据。"
          />
        )}
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>今日重点设备</h3>
            <p>优先看高危、今日变化和待人工确认较多的设备。</p>
          </div>
          <div className="section-meta">共 {focusState.priority_devices.length} 台</div>
        </div>

        {focusState.priority_devices.length > 0 ? (
          <div className="device-focus-list">
            {focusState.priority_devices.map((device, index) => (
              <article key={`${device.asset_ip}-${device.asset_name}`} className="device-focus-row">
                <div className="device-focus-rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="device-focus-main">
                  <div className="device-focus-heading">
                    <div>
                      <strong>{device.asset_name}</strong>
                      <div className="subtle-text">{device.asset_ip}</div>
                    </div>
                    <span className={`badge tone-${mapDevicePriorityTone(device)}`}>{buildDevicePriorityLabel(device)}</span>
                  </div>
                  <p className="device-focus-summary">{buildDevicePrioritySummary(device)}</p>
                </div>
                <div className="device-focus-metrics" aria-label={`${device.asset_name} 风险指标`}>
                  <div>
                    <span>高危</span>
                    <strong>{device.high_count}</strong>
                  </div>
                  <div>
                    <span>变化</span>
                    <strong>{device.today_changes_count}</strong>
                  </div>
                  <div>
                    <span>中危</span>
                    <strong>{device.medium_count}</strong>
                  </div>
                  <div>
                    <span>确认</span>
                    <strong>{device.needs_manual_confirmation_count}</strong>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <StatePanel
            tone="empty"
            title="今天没有需要优先编排的重点设备"
            description="当前活跃工作项为空，设备聚合区域会在出现未处理、处理中或人工确认项时自动更新。"
          />
        )}
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>今日变化</h3>
            <p>关注今日新增问题、端口变化和关键配置变化。</p>
          </div>
          <div className="section-meta">共 {focusState.summary.today_changes_count} 项</div>
        </div>

        {focusState.today_changes.length > 0 ? (
          <div className="list-stack">
            {focusState.today_changes.map((item) =>
              renderFocusItem(item, drafts, messages, savingItemId, updateDraft, handleSave),
            )}
          </div>
        ) : (
          <StatePanel
            tone="empty"
            title="今天没有新增变化项"
            description="今天尚未出现新的 fail、端口变化或关键安全配置变化。"
          />
        )}
      </section>

      <section className="panel-card">
        <div className="section-head">
          <div>
            <h3>本周安排</h3>
            <p>收口中危积压项和人工核查项，避免继续堆积。</p>
          </div>
          <div className="section-meta">共 {focusState.summary.weekly_plan_count} 项</div>
        </div>

        {focusState.weekly_plan.length > 0 ? (
          <div className="list-stack">
            {focusState.weekly_plan.map((item) =>
              renderFocusItem(item, drafts, messages, savingItemId, updateDraft, handleSave),
            )}
          </div>
        ) : (
          <StatePanel
            tone="empty"
            title="本周没有待编排的问题"
            description="当前没有中危积压项或人工核查项。"
          />
        )}
      </section>

      <FocusRiskOverview overview={overview} />
    </div>
  );
}

function renderFocusItem(
  item: DailyFocusItem,
  drafts: Record<string, ItemDraft>,
  messages: Record<string, ItemMessage>,
  savingItemId: string | null,
  updateDraft: (itemId: string, patch: Partial<ItemDraft>) => void,
  handleSave: (item: DailyFocusItem) => Promise<void>,
) {
  const draft = drafts[item.id] ?? { status: item.status, remark: item.remark ?? "" };
  const message = messages[item.id];
  const isSaving = savingItemId === item.id;
  const isDirty = draft.status !== item.status || normalizeRemark(draft.remark) !== normalizeRemark(item.remark ?? "");

  return (
    <article key={item.id} className="focus-item-card">
      <div className="headline-row">
        <strong>{item.headline}</strong>
        <div className="focus-badge-row">
          <span className={`badge tone-${mapSeverityBadge(item.severity)}`}>{formatSeverity(item.severity)}</span>
          <span className={`badge tone-${mapStatusBadge(item.status)}`}>{formatStatus(item.status)}</span>
        </div>
      </div>

      <p>{item.summary}</p>

      <div className="focus-tags">
        <span className={`status-chip tone-${mapSeverityTone(item.severity)}`}>{formatSeverity(item.severity)}</span>
        <span className="status-chip tone-neutral">{formatDateTime(item.detected_at)}</span>
        {item.persistent_days >= 2 ? (
          <span className="status-chip tone-neutral">{formatPersistentDays(item.persistent_days)}</span>
        ) : null}
        {item.updated_at ? (
          <span className="status-chip tone-neutral">
            {`更新于 ${formatDateTime(item.updated_at)}${item.updated_by ? ` / ${item.updated_by}` : ""}`}
          </span>
        ) : null}
      </div>

      <div className="focus-edit-grid">
        <label className="focus-edit-field">
          <span>处理状态</span>
          <select value={draft.status} onChange={(event) => updateDraft(item.id, { status: event.target.value as DailyFocusItemStatus })}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="focus-edit-field focus-edit-field-wide">
          <span>处理备注</span>
          <textarea
            rows={2}
            value={draft.remark}
            placeholder="补充处理动作、判断依据或待确认点"
            onChange={(event) => updateDraft(item.id, { remark: event.target.value })}
          />
        </label>
      </div>

      <div className="focus-save-row">
        <button
          type="button"
          className="primary-button"
          disabled={isSaving || !isDirty}
          onClick={() => void handleSave(item)}
        >
          {isSaving ? "保存中..." : "保存状态"}
        </button>
        {message ? (
          <span className={`status-chip tone-${message.tone === "error" ? "high" : "good"}`}>{message.text}</span>
        ) : null}
      </div>
    </article>
  );
}

function buildDraftMap(focus: DailyFocus): Record<string, ItemDraft> {
  const items = [
    ...focus.today_must_handle.flatMap((group) => group.items),
    ...focus.today_changes,
    ...focus.weekly_plan,
  ];
  return items.reduce<Record<string, ItemDraft>>((map, item) => {
    map[item.id] = {
      status: item.status,
      remark: item.remark ?? "",
    };
    return map;
  }, {});
}

function buildDevicePrioritySummary(device: DailyFocusPriorityDevice): string {
  if (device.high_count > 0) {
    return `优先处理 ${device.high_count} 项高危问题，并同步关注 ${device.today_changes_count} 项今日变化。`;
  }
  if (device.needs_manual_confirmation_count > 0) {
    return `当前以人工核查为主，待确认 ${device.needs_manual_confirmation_count} 项，建议先补充判断依据。`;
  }
  if (device.today_changes_count > 0) {
    return `今天出现 ${device.today_changes_count} 项变化，建议先确认是否为预期变更。`;
  }
  return `以中危积压清理为主，当前共有 ${device.medium_count} 项待安排。`;
}

function buildDevicePriorityLabel(device: DailyFocusPriorityDevice): string {
  if (device.high_count > 0) {
    return "优先处置";
  }
  if (device.needs_manual_confirmation_count > 0) {
    return "待人工确认";
  }
  if (device.today_changes_count > 0) {
    return "关注变化";
  }
  return "计划清理";
}

function mapDevicePriorityTone(device: DailyFocusPriorityDevice): "critical" | "medium" | "info" {
  if (device.high_count > 0) {
    return "critical";
  }
  if (device.today_changes_count > 0 || device.needs_manual_confirmation_count > 0) {
    return "medium";
  }
  return "info";
}

function normalizeRemark(value: string): string {
  return value.trim();
}

function mapSeverityTone(severity: string): "good" | "medium" | "high" | "neutral" {
  const normalized = severity.trim().toLowerCase();
  if (normalized === "high") {
    return "high";
  }
  if (normalized === "medium") {
    return "medium";
  }
  if (normalized === "low") {
    return "good";
  }
  return "neutral";
}

function mapSeverityBadge(severity: string): "critical" | "medium" | "low" | "info" {
  const normalized = severity.trim().toLowerCase();
  if (normalized === "high") {
    return "critical";
  }
  if (normalized === "medium") {
    return "medium";
  }
  if (normalized === "low") {
    return "low";
  }
  return "info";
}

function mapStatusBadge(status: DailyFocusItemStatus): "info" | "medium" | "critical" | "low" | "normal" {
  if (status === "pending") {
    return "info";
  }
  if (status === "in_progress") {
    return "medium";
  }
  if (status === "resolved") {
    return "normal";
  }
  if (status === "ignored") {
    return "low";
  }
  return "critical";
}

function formatSeverity(severity: string): string {
  const normalized = severity.trim().toLowerCase();
  if (normalized === "high") {
    return "高危";
  }
  if (normalized === "medium") {
    return "中危";
  }
  if (normalized === "low") {
    return "低危";
  }
  return severity || "--";
}

function formatStatus(status: DailyFocusItemStatus): string {
  if (status === "pending") {
    return "未处理";
  }
  if (status === "in_progress") {
    return "处理中";
  }
  if (status === "resolved") {
    return "已处理";
  }
  if (status === "ignored") {
    return "已忽略";
  }
  return "需人工确认";
}

function formatPersistentDays(days: number): string {
  if (days >= 2) {
    return `连续 ${days} 天`;
  }
  return "--";
}
