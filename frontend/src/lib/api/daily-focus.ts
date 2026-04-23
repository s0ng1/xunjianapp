import { fetchFromApi } from "./client";

export type DailyFocusItemStatus =
  | "pending"
  | "in_progress"
  | "resolved"
  | "ignored"
  | "needs_manual_confirmation";

export type DailyFocusItem = {
  id: string;
  asset_id: number | null;
  asset_name: string;
  asset_ip: string;
  section: "today_must_handle" | "today_changes" | "weekly_plan";
  priority_rank: number;
  severity: string;
  headline: string;
  summary: string;
  detected_at: string;
  source_type: string;
  rule_id: string | null;
  persistent_days: number;
  status: DailyFocusItemStatus;
  remark: string | null;
  updated_at: string | null;
  updated_by: string | null;
};

export type DailyFocusAssetGroup = {
  asset_id: number | null;
  asset_name: string;
  asset_ip: string;
  items: DailyFocusItem[];
};

export type DailyFocusPriorityDevice = {
  asset_id: number | null;
  asset_name: string;
  asset_ip: string;
  high_count: number;
  medium_count: number;
  today_changes_count: number;
  needs_manual_confirmation_count: number;
};

export type DailyFocusItemState = {
  item_id: string;
  reference_date: string;
  status: DailyFocusItemStatus;
  remark: string | null;
  updated_at: string;
  updated_by: string;
};

export type DailyFocusItemStateUpdatePayload = {
  reference_date: string;
  status: DailyFocusItemStatus;
  remark?: string;
  updated_by?: string;
};

export type DailyFocus = {
  reference_date: string;
  generated_at: string;
  today_summary: string;
  summary: {
    must_handle_count: number;
    today_changes_count: number;
    weekly_plan_count: number;
  };
  priority_devices: DailyFocusPriorityDevice[];
  today_must_handle: DailyFocusAssetGroup[];
  today_changes: DailyFocusItem[];
  weekly_plan: DailyFocusItem[];
};

export const dailyFocusApi = {
  get: (referenceDate?: string) => {
    const query = referenceDate ? `?reference_date=${encodeURIComponent(referenceDate)}` : "";
    return fetchFromApi<DailyFocus>(`/api/v1/daily-focus${query}`);
  },

  updateItemState: (itemId: string, payload: DailyFocusItemStateUpdatePayload) =>
    fetchFromApi<DailyFocusItemState>(`/api/v1/daily-focus/items/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      body: payload,
    }),
};
