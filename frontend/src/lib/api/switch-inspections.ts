import { fetchFromApi } from "./client";
import type { SwitchInspection } from "./inspections";

export type SwitchInspectionSubmitPayload = {
  ip: string;
  username: string;
  password: string;
  vendor: "h3c";
  port?: number;
};

export async function apiSubmitSwitchInspection(
  payload: SwitchInspectionSubmitPayload,
): Promise<SwitchInspection> {
  return fetchFromApi<SwitchInspection>("/api/v1/switch-inspections/run", {
    method: "POST",
    body: payload,
  });
}
