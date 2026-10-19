export type MonitorConfig = {
  name: string;
  url: string;
  interval_seconds: number;
  timeout_seconds: number;
  expected_status: number;
  expected_body: string | null;
  failure_threshold: number;
};
export type Monitor = MonitorConfig & {
  id: string;
  state: string;
  config_version: number;
  run_requested: boolean;
  is_running: boolean;
  last_status_code: number | null;
  last_response_ms: number | null;
  last_checked_at: string | null;
  consecutive_failures: number;
};
export type Group = {
  id: string;
  name: string;
  monitor_ids: string[];
  recipients: string[];
  state: string;
  config_version: number;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail))
        message = data.detail
          .map(
            (issue: { loc: string[]; msg: string }) =>
              `${issue.loc.slice(1).join(".")}: ${issue.msg}`,
          )
          .join("; ");
    } catch {
      /* response may not contain JSON */
    }
    throw new ApiError(message, response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
