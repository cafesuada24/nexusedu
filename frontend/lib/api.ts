import { toast } from "sonner";

/**
 * Backend API client for the NexusEDU intervention service.
 *
 * Endpoints (per src/DEMO_UIXx8/ENDPOINTS.md / frontend/ENDPOINTS_concise.md):
 *   POST   /data/ingest                — push raw test rows (wrapped).
 *   GET    /alerts                     — pull current at-risk students + status.
 *   PATCH  /alerts/{sid}/status        — update a student's intervention status.
 *   POST   /alerts/{sid}/draft         — trigger async draft generation (returns job_id).
 *   GET    /jobs/{job_id}              — poll status/result for background jobs.
 *   POST   /alerts/{sid}/send          — send email for student.
 *   POST   /query                      — async agent query (returns job_id).
 *   GET    /advisors/leaderboard       — leaderboard by time window.
 *   POST   /auth/register              — register (public)
 *   POST   /auth/jwt/login             — login (form data) returns { access_token, token_type }
 *   GET    /users/me                   — get current user (requires token)
 *
 * The base URL comes from `NEXT_PUBLIC_API_BASE_URL`; if missing we default
 * to the documented `/api/v1` base path.
 */

export type BackendInterventionStatus =
  | "none"
  | "new"
  | "sent"
  | "booked"
  | "supporting"
  | "resolved"
  | "expired";

export type BackendRiskStatus =
  | "Significant Drop"
  | "Mild Drop"
  | "Stable"
  | (string & {});

export type BackendAlert = {
  sid: string;
  student_name: string;
  email: string;
  current_risk_status: BackendRiskStatus;
  intervention_status: BackendInterventionStatus;
  draft_job_id?: string | null;
  draft_subject?: string | null;
  draft_body?: string | null;
};

/** One row of the canonical student-test schema sent to /data/ingest records. */
export type BackendIngestRow = {
  sid: string;
  student_name: string;
  course_id: string;
  course_name: string;
  test_type: string;
  email: string;
  last_notified_timestamp: number;
  last_notified_satisfaction: number;
  score: number;
  timestamp: number;
  academic_year: number;
  semester: number;
};


export type JobResult = {
  job_id: string;
  status: "processing" | "completed" | "failed" | string;
  result?: any;
  error?: string | null;
};

export type AdvisorLeaderboardItem = {
  advisor_id: string;
  name: string;
  total_points: number;
  actions_count: number;
  sent_count: number;
  resolved_count: number;
};

export type UserRead = {
  id: string;
  email: string;
  role?: "admin" | "advisor" | "viewer";
  // Add other fields returned by /users/me as needed.
};

/* ----------------------------------------------------------------------- */
/*  Configuration                                                          */
/* ----------------------------------------------------------------------- */

const DEFAULT_TIMEOUT_MS = 10_000;
const INGEST_TIMEOUT_MS = 60_000;

/**
 * LocalStorage key used to persist the JWT token on the client.
 * We keep this internal to the API module to avoid sprinkling the key around.
 */
const TOKEN_STORAGE_KEY = "nexusedu:auth:token";

function getApiBase(): string {
  // Use environment override when present, else default to documented /api/v1.
  const env =
    typeof process !== "undefined"
      ? // Access runtime build-time env variable in Next.js
        // Note: in Next.js, env variables prefixed with NEXT_PUBLIC_ are exposed to the browser.
        (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined)
      : undefined;
  if (env && env.trim()) return env.trim().replace(/\/+$/, "");
  // Default to the documented base path so the demo UI works without extra config.
  return "/api/v1";
}

function endpoint(path: string): string {
  const base = getApiBase();
  // Ensure we don't create double slashes
  if (!base) return path;
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

async function withTimeout<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  ms: number,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fn(controller.signal);
  } finally {
    clearTimeout(timer);
  }
}

/* ----------------------------------------------------------------------- */
/*  Auth helpers                                                           */
/* ----------------------------------------------------------------------- */

/**
 * Return token stored in localStorage (if available).
 * Using localStorage keeps calls simple for the demo. If your deployment
 * uses httpOnly cookies you can adapt authFetch to omit this and rely
 * on cookies being sent by the browser.
 */
export function getAuthToken(): string | null {
  // if (typeof window === "undefined") return null;
  try {
    const t = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    return t && t.length > 0 ? t : null;
  } catch {
    return null;
  }
}

/** Persist a JWT token for use on subsequent requests. */
export function setAuthToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (!token) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // ignore localStorage errors
  }
}

/** Clear stored token. */
export function clearAuthToken() {
  setAuthToken(null);
}

/**
 * authFetch behaves like fetch but injects Authorization header when a JWT
 * token is available. It merges headers and accepts all the same fetch options.
 * We still use withTimeout around calls for predictable behavior.
 */
export async function authFetch(
  url: string,
  opts: RequestInit = {},
  signal?: AbortSignal,
): Promise<Response> {
  // Always get the freshest token from localStorage if not explicitly provided
  const token = getAuthToken();
  const headers = new Headers(opts.headers || undefined);
  headers.set("Accept", headers.get("Accept") || "application/json");
  console.log(headers)
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const merged: RequestInit = {
    ...opts,
    headers,
    signal: opts.signal ?? signal,
  };

  const res = await fetch(url, merged);

  // Global 401 handling: we log it. The AuthProvider
  // or useProfile hook will handle redirecting to login if the session is truly invalid.
  if (res.status === 401) {
    warnLog("authFetch: 401 Unauthorized", url);
  }

  return res;
}
/* ----------------------------------------------------------------------- */
/*  Utility                                                                */
/* ----------------------------------------------------------------------- */

function warnLog(...args: any[]) {
  // eslint-disable-next-line no-console
  console.warn("[lib/api]", ...args);
}

/* ----------------------------------------------------------------------- */
/*  Auth API: register / login / me                                         */
/* ----------------------------------------------------------------------- */

/**
 * Login using the backend's JWT form login.
 * The endpoint expects form-encoded fields `username` and `password`.
 * On success we persist the token via setAuthToken and return the parsed body.
 */
export async function login(
  username: string,
  password: string,
): Promise<{ access_token: string; token_type: string } | null> {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);

  const res = await withTimeout(
    (signal) =>
      fetch(endpoint("/auth/jwt/login"), {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        },
        body: form.toString(),
        signal,
      }),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Đăng nhập thất bại: ${message}`);
  }

  const body = await res.json();
  if (body?.access_token) {
    setAuthToken(body.access_token);
  }
  return body;
}

/**
 * Register a new user. Returns parsed response or throws on non-ok.
 * Per ENDPOINTS_concise.md: POST /auth/register with JSON body { email, password }.
 */
export async function register(email: string, password: string): Promise<any> {
  const res = await withTimeout(
    (signal) =>
      fetch(endpoint("/auth/register"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ email, password }),
        signal,
      }),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Đăng ký thất bại: ${message}`);
  }
  return res.json();
}

/**
 * GET /users/me — returns the current user profile and role.
 * Requires a valid token; authFetch will attach Authorization header.
 */
export async function getCurrentUser(): Promise<UserRead | null> {
  const res = await withTimeout(
    (signal) => authFetch(endpoint("/users/me"), { method: "GET" }, signal),
    DEFAULT_TIMEOUT_MS,
  );
  
  if (!res.ok) {
    if (res.status === 401) return null;
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch user: ${res.status}`);
  }
  
  const data = await res.json();
  return data as UserRead;
}

/* ----------------------------------------------------------------------- */
/*  Public API                                                             */
/* ----------------------------------------------------------------------- */

/**
 * Sends multi-source data to the backend for ingestion.
 *
 * The payload follows the DataIngestionRequest schema:
 * {
 *   batch_id: string,
 *   upload_timestamp: string,
 *   data_sources: [
 *     { source_type: "sis", records: SISRecord[] },
 *     { source_type: "lms", records: LMSRecord[] },
 *     { source_type: "custom", table_name: string, records: any[] }
 *   ]
 * }
 */
export async function ingestData(dataSources: {
  source_type: "sis" | "lms" | "custom";
  table_name?: string;
  records: any[];
}[]): Promise<void> {
  if (dataSources.length === 0) return;
  const payload = {
    batch_id: `batch_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    upload_timestamp: new Date().toISOString(),
    data_sources: dataSources,
  };

  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/data/ingest"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        signal,
      ),
    INGEST_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Đồng bộ dữ liệu thất bại: ${message}`);
  }
}

/**
 * Sends parsed CSV rows to the backend for long-term storage and analysis.
 * @deprecated Use ingestData for multi-source support.
 */
export async function ingestRows(rows: BackendIngestRow[]): Promise<void> {
  return ingestData([
    {
      source_type: "custom",
      table_name: "ingest_rows",
      records: rows,
    },
  ]);
}

/**
 * Pulls the current authoritative list of at-risk students from the backend.
 * Returns an empty array on failure or malformed response (keeps UI usable).
 */
export async function fetchAlerts(): Promise<BackendAlert[]> {
  const res = await withTimeout(
    (signal) => authFetch(endpoint("/alerts"), { method: "GET" }, signal),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy danh sách cảnh báo: ${message}`);
  }
  const data = await res.json();
  if (!Array.isArray(data)) return [];
  return (data as BackendAlert[]).filter(
    (a) => typeof a?.sid === "string" && a.sid.length > 0,
  );
}

/**
 * Pushes a status transition for a single student. Backend is the source of
 * truth for status, so this is fired on every Kanban move.
 */
export async function updateAlertStatus(
  sid: string,
  status: BackendInterventionStatus,
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/alerts/${encodeURIComponent(sid)}/status`),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Cập nhật trạng thái thất bại: ${message}`);
  }
}

/* ----------------------------------------------------------------------- */
/*  Async jobs & other endpoints                                           */
/* ----------------------------------------------------------------------- */

/**
 * { job_id, status, result?, error? }
 */
export async function getJobStatus(job_id: string): Promise<JobResult> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/jobs/${encodeURIComponent(job_id)}`),
        {
          method: "GET",
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    throw new Error(`Kiểm tra trạng thái job thất bại: ${res.status}`);
  }
  return (await res.json()) as JobResult;
}

/**
 * Send finalized email body to student and transition the student's status
 * to `sent` on the server. Expects { body: "..." } per ENDPOINTS.md.
 */
export async function sendNudge(
  sid: string,
  body: { body: string },
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/alerts/${encodeURIComponent(sid)}/send`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Gửi email thất bại: ${message}`);
  }
}

/**
 * POST /query — ask the async AI agent for analysis. Returns { job_id, status }.
 * Caller should poll /jobs/{job_id}.
 */
export async function queryAgent(
  query: string,
  opts?: { thread_id?: string },
): Promise<DraftJobResponse> {
  const payload: Record<string, any> = { query };
  if (opts?.thread_id) payload.thread_id = opts.thread_id;

  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/query"),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Truy vấn AI thất bại: ${message}`);
  }
  return (await res.json()) as DraftJobResponse;
}

/**
 * GET /advisors/leaderboard[?time_window=...] — returns advisor leaderboard.
 */
export async function fetchAdvisorsLeaderboard(
  time_window?: "weekly" | "monthly" | "semester" | "all_time",
): Promise<AdvisorLeaderboardItem[]> {
  const qp = time_window
    ? `?time_window=${encodeURIComponent(time_window)}`
    : "";
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/advisors/leaderboard${qp}`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy bảng xếp hạng: ${message}`);
  }
  const data = await res.json();
  if (!Array.isArray(data)) return [];
  return data as AdvisorLeaderboardItem[];
}

/* ----------------------------------------------------------------------- */
/*  Helpers                                                                */
/* ----------------------------------------------------------------------- */

/** True when an `NEXT_PUBLIC_API_BASE_URL` was configured at build time or we're in the browser. */
export function isApiConfigured(): boolean {
  // If we're in the browser, we assume the default /api/v1 rewrite works.
  if (typeof window !== "undefined") return true;

  const env =
    typeof process !== "undefined"
      ? (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined)
      : undefined;
  return Boolean(env && env.trim());
}


export type AdvisorEngagementItem = {
  faculty: string;
  sent: number;
  drafted: number;
};

/**
 * GET /advisors/engagement — returns engagement metrics by faculty/major.
 */
export async function fetchAdvisorsEngagement(): Promise<AdvisorEngagementItem[]> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/advisors/engagement"),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy dữ liệu tương tác: ${message}`);
  }
  const data = await res.json();
  if (!Array.isArray(data)) return [];
  return data as AdvisorEngagementItem[];
}

export type KpiStats = {
  retention_rate: number;
  total_interventions: number;
  advisor_engagement: number;
  dropout_rate: number;
  total_students: number;
};

export type RetentionTrendItem = {
  month: string;
  baseline: number;
  current: number;
};

/**
 * GET /metrics/stats — returns high-level dashboard KPIs.
 */
export async function fetchKpiStats(): Promise<KpiStats> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/metrics/stats"),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy chỉ số KPI: ${message}`);
  }
  return (await res.json()) as KpiStats;
}

/**
 * GET /metrics/retention — returns retention trend data.
 */
export async function fetchRetentionTrend(): Promise<RetentionTrendItem[]> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/metrics/retention"),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy xu hướng giữ chân: ${message}`);
  }
  const data = await res.json();
  if (!Array.isArray(data)) return [];
  return data as RetentionTrendItem[];
}

export type EmailHistoryItem = {
  email_id: string;
  subject: string;
  body: string;
  status: "draft" | "sent";
  created_at: string;
  sent_at: string | null;
};

/**
 * GET /alerts/{sid}/history — returns communication history for a student.
 */
export async function fetchAlertHistory(sid: string): Promise<EmailHistoryItem[]> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/alerts/${encodeURIComponent(sid)}/history`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy lịch sử email: ${message}`);
  }
  const data = await res.json();
  if (!Array.isArray(data)) return [];
  return data as EmailHistoryItem[];
}

export type DraftStatusResponse = {
  sid: string;
  is_generating: boolean;
  subject: string | null;
  body: string | null;
};

/**
 * GET /alerts/{sid}/draft — returns current draft status and content.
 */
export async function fetchDraftStatus(sid: string): Promise<DraftStatusResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/alerts/${encodeURIComponent(sid)}/draft`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy trạng thái bản nháp: ${message}`);
  }
  return (await res.json()) as DraftStatusResponse;
}
