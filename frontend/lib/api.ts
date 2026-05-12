import { AdvisorLeaderboard } from "@/components/dashboard/advisor-leaderboard";
import { z } from "zod";

import { SlotTakenError } from "@/lib/appointments";

/**
 * Backend API client for the NexusEDU intervention service.
 *
 * Endpoints (per src/DEMO_UIXx8/ENDPOINTS.md / frontend/ENDPOINTS_concise.md):
 *   POST   /data/ingest                — push raw test rows (wrapped).
 *   GET    /cases/open                 — pull open cases (new tab).
 *   GET    /cases/assigned             — pull assigned cases.
 *   PATCH  /cases/{case_id}/status     — update a case status.
 *   POST   /cases/{case_id}/draft      — trigger async draft generation (returns job_id).
 *   GET    /jobs/{job_id}              — poll status/result for background jobs.
 *   POST   /cases/{case_id}/send       — send email for case.
 *   POST   /query                      — async agent query (returns job_id).
 *   GET    /advisors/leaderboard       — leaderboard by time window.
 *   POST   /auth/register              — register (public)
 *   POST   /auth/jwt/login             — login (form data) returns { access_token, token_type }
 *   GET    /users/me                   — get current user (requires token)
 *
 * The base URL comes from `NEXT_PUBLIC_API_BASE_URL`; if missing we default
 * to the documented `/api/v1` base path.
 */

/* ----------------------------------------------------------------------- */
/*  Schemas & Types                                                        */
/* ----------------------------------------------------------------------- */

export const BackendInterventionStatusSchema = z.enum([
  "new",
  "accepted",
  "booked",
  "sent",
  "supporting",
  "resolved",
  "dismissed",
  "expired",
]);
export type BackendInterventionStatus = z.infer<
  typeof BackendInterventionStatusSchema
>;
export const AppointmentSchema = z.object({
  appointment_time: z.string(),
  duration_minutes: z.number(),
  meeting_method: z.enum(["online", "in_person"]),
  notes: z.string().nullable().optional(),
});
export type Appointment = z.infer<typeof AppointmentSchema>;

export const TaskItemBaseSchema = z.object({
  case_id: z.string(),
  created_at: z.string(),
  sid: z.string(),
  assigned_advisor_id: z.string().nullable().optional(),
  assigned_to: z.string().nullable().optional(),
  student_name: z.string().nullable().optional(),
  major: z.string().nullable().optional(),
  current_risk_status: z.string().nullable().optional(),
  intervention_status: z.string().nullable().optional(),
  email: z.any().nullable().optional(),
  appointment: AppointmentSchema.nullable().optional(),
});

export const TaskItemSchema = TaskItemBaseSchema.transform((data) => {
  let emailStr = "";
  let draft_subject = null;
  let draft_body = null;
  let draft_status = null;

  if (data.email && typeof data.email === "object") {
    emailStr = data.email.recipent || data.email.recipient || "";
    draft_subject = data.email.subject || null;
    draft_body = data.email.body || null;
    draft_status = data.email.status || null;
  } else if (typeof data.email === "string") {
    emailStr = data.email;
  }

  return {
    ...data,
    email: emailStr,
    draft_subject,
    draft_body,
    draft_status,
    points_reward: 0,
    appointment: data.appointment || null,
  };
});
export type TaskItem = z.infer<typeof TaskItemSchema>;

export const TaskPagedResponseSchema = z.object({
  items: z.array(TaskItemSchema).optional().default([]),
  metadata: z
    .object({
      total_count: z.number().optional().default(0),
      limit: z.number().optional().default(20),
      offset: z.number().optional().default(0),
      has_next: z.boolean().optional().default(false),
    })
    .optional()
    .default({}),
});
export type TaskPagedResponse = z.infer<typeof TaskPagedResponseSchema>;

export const BackendIngestRowSchema = z.object({
  sid: z.string(),
  student_name: z.string(),
  course_id: z.string(),
  course_name: z.string(),
  test_type: z.string(),
  email: z.string(),
  last_notified_timestamp: z.number(),
  last_notified_satisfaction: z.number(),
  score: z.number(),
  timestamp: z.number(),
  academic_year: z.number(),
  semester: z.number(),
});
export type BackendIngestRow = z.infer<typeof BackendIngestRowSchema>;

export const JobResultSchema = z.object({
  job_id: z.string(),
  status: z.string(),
  progress: z.number().optional(),
  created_at: z.string().nullable().optional(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  result: z.any().optional(),
  error: z.string().nullable().optional(),
});
export type JobResult = z.infer<typeof JobResultSchema>;

export const CaseResponseSchema = z.object({
  case_id: z.string(),
  sid: z.string(),
  status: z.string(),
  created_at: z.string(),
  resolved_at: z.string().nullable().optional(),
});
export type CaseResponse = z.infer<typeof CaseResponseSchema>;

export const EmailHistoryItemSchema = z.object({
  email_id: z.string(),
  subject: z.string(),
  body: z.string(),
  status: z.enum(["generating", "draft", "sent"]),
  created_at: z.string(),
  sent_at: z.string().nullable(),
});
export type EmailHistoryItem = z.infer<typeof EmailHistoryItemSchema>;


export const CaseDetailsResponseSchema = CaseResponseSchema.extend({
  email: EmailHistoryItemSchema.nullable().optional(),
  appointment: AppointmentSchema.nullable().optional(),
});
export type CaseDetailsResponse = z.infer<typeof CaseDetailsResponseSchema>;

export const DraftJobResponseSchema = z.object({
  job_id: z.string(),
  status: z.string(),
});
export type DraftJobResponse = z.infer<typeof DraftJobResponseSchema>;

export const AdvisorLeaderboardItemSchema = z.object({
  advisor_id: z.string(),
  name: z.string(),
  total_points: z.number(),
  actions_count: z.number(),
  sent_count: z.number(),
  resolved_count: z.number(),
});
export type AdvisorLeaderboardItem = z.infer<
  typeof AdvisorLeaderboardItemSchema
>;

export const AdvisorLeaderboardSchema = z.object({
  items: z.array(AdvisorLeaderboardItemSchema),
  metadata: z.object({
    total_count: z.number().int().gte(0),
    limit: z.number().int().gte(0),
    offset: z.number().int().gte(0),
    has_next: z.boolean(),
  }),
});
export type AdvisorLeaderboard = z.infer<typeof AdvisorLeaderboardSchema>;

export const UserReadSchema = z.object({
  id: z.string(),
  email: z.string(),
  role: z.enum(["admin", "advisor", "viewer"]).optional(),
});
export type UserRead = z.infer<typeof UserReadSchema>;

export const UserSettingsSchema = z.object({
  auto_draft_enabled: z.boolean(),
});
export type UserSettings = z.infer<typeof UserSettingsSchema>;

export const AdvisorPointsSchema = z.object({
  points: z.number().int(),
});
export type AdvisorPoints = z.infer<typeof AdvisorPointsSchema>;

export const AdvisorProfileReadSchema = z.object({
  advisor_id: z.string(),
  name: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  faculty: z.string().nullable().optional(),
  office: z.string().nullable().optional(),
  bio: z.string().nullable().optional(),
});
export type AdvisorProfileRead = z.infer<typeof AdvisorProfileReadSchema>;

export const AdvisorProfileUpdateSchema = z.object({
  name: z.string().nullable().optional(),
  title: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  faculty: z.string().nullable().optional(),
  office: z.string().nullable().optional(),
  bio: z.string().nullable().optional(),
});
export type AdvisorProfileUpdate = z.infer<typeof AdvisorProfileUpdateSchema>;

export const WorkingHoursReadSchema = z.object({
  id: z.string(),
  day_of_week: z.number(),
  start_time: z.string(), // "HH:MM:SS"
  end_time: z.string(),
  timezone: z.string(),
});
export type WorkingHoursRead = z.infer<typeof WorkingHoursReadSchema>;

export const DayOffReadSchema = z.object({
  id: z.string(),
  date: z.string(), // "YYYY-MM-DD"
  reason: z.string().nullable().optional(),
});
export type DayOffRead = z.infer<typeof DayOffReadSchema>;

export const AdvisorScheduleReadSchema = z.object({
  working_hours: z.array(WorkingHoursReadSchema),
  days_off: z.array(DayOffReadSchema),
});
export type AdvisorScheduleRead = z.infer<typeof AdvisorScheduleReadSchema>;

export const WorkingHoursCreateSchema = z.object({
  day_of_week: z.number(),
  start_time: z.string(),
  end_time: z.string(),
  timezone: z.string().default("UTC"),
});
export type WorkingHoursCreate = z.infer<typeof WorkingHoursCreateSchema>;

export const WorkingHoursUpdateSchema = z.object({
  day_of_week: z.number(),
  start_time: z.string(),
  end_time: z.string(),
  timezone: z.string(),
});
export type WorkingHoursUpdate = z.infer<typeof WorkingHoursUpdateSchema>;

export const DayOffCreateSchema = z.object({
  date: z.string(),
  reason: z.string().nullable().optional(),
});
export type DayOffCreate = z.infer<typeof DayOffCreateSchema>;


export const KpiStatsSchema = z.object({
  retention_rate: z.number(),
  total_interventions: z.number(),
  advisor_engagement: z.number(),
  dropout_rate: z.number(),
  total_students: z.number(),
});
export type KpiStats = z.infer<typeof KpiStatsSchema>;

export const RetentionTrendItemSchema = z.object({
  month: z.string(),
  baseline: z.number(),
  current: z.number(),
});
export type RetentionTrendItem = z.infer<typeof RetentionTrendItemSchema>;

// Backend GET /cases/{case_id}/email returns QueryEmailDTO shape
const _QueryEmailDTOSchema = z.object({
  email_id: z.string(),
  recipent: z.string().optional(),
  subject: z.string().nullable().optional(),
  body: z.string().nullable().optional(),
  status: z.string(),
  created_at: z.string().optional(),
  sent_at: z.string().nullable().optional(),
});

export const DraftStatusResponseSchema = _QueryEmailDTOSchema.transform(
  (d) => ({
    subject: d.subject ?? null,
    body: d.body ?? null,
    is_generating: d.status === "generating",
    status: d.status,
  }),
);
export type DraftStatusResponse = z.infer<typeof DraftStatusResponseSchema>;

/* ----------------------------------------------------------------------- */
/*  Configuration                                                          */
/* ----------------------------------------------------------------------- */

export const DEFAULT_TIMEOUT_MS = 10_000;
const INGEST_TIMEOUT_MS = 60_000;

/**
 * LocalStorage key used to persist the JWT token on the client.
 * We keep this internal to the API module to avoid sprinkling the key around.
 */
const TOKEN_STORAGE_KEY = "nexusedu:auth:token";

function getApiBase(): string {
  // On the client, we MUST use the relative proxy path so that proxy.ts can
  // intercept the request, extract the httpOnly cookie, and inject the Bearer token.
  if (typeof window !== "undefined") {
    return "/api/v1";
  }

  // On the server, we can talk directly to the backend URL to avoid double-proxying.
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env && env.trim()) {
    const base = env.trim().replace(/\/+$/, "");
    if (base.startsWith("/")) {
      return `http://localhost:8000${base}`;
    }
    return base;
  }

  return (new URL("http://localhost:8000/api/v1")).origin.replace("://localhost", "://127.0.0.1");
}

export function endpoint(path: string): string {
  const base = getApiBase();
  // Ensure we don't create double slashes
  if (!base) return path;
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export async function withTimeout<T>(
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
 * Get token (server-side only helper).
 * Client-side should rely on cookies being sent automatically.
 */
export async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    try {
      const { cookies } = await import("next/headers");
      const cookieStore = await cookies();
      return cookieStore.get("nexusedu_auth_token")?.value ?? null;
    } catch {
      return null;
    }
  }
  return null; // Client cannot read httpOnly cookies
}

/**
 * @deprecated Use /api/auth/login route instead.
 * This is kept for compatibility during refactor but will now be a no-op on client.
 */
export function setAuthToken(token: string | null) {
  if (typeof window !== "undefined") {
    if (!token) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  }
}

/** Clear stored token. */
export async function logout() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    await fetch("/api/auth/logout", { method: "POST" });
  }
}

/**
 * authFetch behaves like fetch but injects Authorization header when a JWT
 * token is available. It merges headers and accepts all the same fetch options.
 */
export async function authFetch(
  url: string,
  opts: RequestInit & { suppressUnauthorizedEvent?: boolean } = {},
  signal?: AbortSignal,
): Promise<Response> {
  const { suppressUnauthorizedEvent, ...fetchOpts } = opts;
  const headers = new Headers(fetchOpts.headers || undefined);
  headers.set("Accept", headers.get("Accept") || "application/json");

  // On the server, we must manually inject the token from cookies
  if (typeof window === "undefined") {
    const token = await getAuthToken();
    if (token) {
      // headers.set("Authorization", `Bearer ${token}`);
      headers.set("Cookie", `nexusedu_auth_token=${token}`);
    }
  }
  // On the client, we rely on middleware to inject the token from the httpOnly cookie
  // for all requests to /api/v1/*

  const merged: RequestInit = {
    ...fetchOpts,
    headers,
    signal: fetchOpts.signal ?? signal,
  };

  const res = await fetch(url, merged);

  if (
    (res.status === 401 || res.status === 403) &&
    !suppressUnauthorizedEvent
  ) {
    warnLog(`authFetch: ${res.status} Unauthorized/Forbidden`, url);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("nexusedu:unauthorized"));
    }
  }

  return res;
}

/* ----------------------------------------------------------------------- */
/*  Utility                                                                */
/* ----------------------------------------------------------------------- */

function warnLog(...args: any[]) {
  console.warn("[lib/api]", ...args);
}

/* ----------------------------------------------------------------------- */
/*  Auth API: register / login / me                                         */
/* ----------------------------------------------------------------------- */

/**
 * Login using the Next.js API route which sets an httpOnly cookie.
 */
export async function login(
  username: string,
  password: string,
): Promise<{ success: boolean } | null> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Đăng nhập thất bại: ${message}`);
  }

  return res.json();
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
        headers: { "Content-Type": "application/json" },
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
    (signal) =>
      authFetch(
        endpoint("/users/me"),
        { method: "GET", suppressUnauthorizedEvent: true },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    if (res.status === 401 || res.status === 403) return null;
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch user: ${res.status}`,
    );
  }

  const data = await res.json();
  return UserReadSchema.parse(data);
}

/**
 * GET /users/me/settings — returns current user settings.
 */
export async function getUserSettings(): Promise<UserSettings> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/users/me/settings"),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch user settings: ${res.status}`,
    );
  }

  const data = await res.json();
  return UserSettingsSchema.parse(data);
}

/**
 * PATCH /users/me/settings — updates current user settings.
 */
export async function updateUserSettings(
  settings: Pick<UserSettings, "auto_draft_enabled">,
): Promise<UserSettings> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/users/me/settings"),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(settings),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to update user settings: ${res.status}`,
    );
  }

  const data = await res.json();
  return UserSettingsSchema.parse(data);
}

/* ----------------------------------------------------------------------- */
/*  Public API                                                             */
/* ----------------------------------------------------------------------- */

/**
 * Sends multi-source data to the backend for ingestion.
 */
export async function ingestData(
  dataSources: {
    source_type: "sis" | "lms" | "custom";
    table_name?: string;
    records: any[];
  }[],
): Promise<void> {
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
 * Pulls the unified list of tasks for the advisor dashboard.
 * Defaults to open (unassigned) cases if no specific type is requested.
 */
export async function fetchTasks(
  limit: number = 20,
  offset: number = 0,
): Promise<TaskPagedResponse> {
  return fetchOpenCases(limit, offset);
}

/**
 * Pulls the list of open (unassigned) cases for the advisor dashboard.
 */
export async function fetchOpenCases(
  limit: number = 20,
  offset: number = 0,
): Promise<TaskPagedResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/open?limit=${limit}&offset=${offset}`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy danh sách case đang mở: ${message}`);
  }
  const data = await res.json();
  return TaskPagedResponseSchema.parse(data);
}

/**
 * Pulls the list of all cases for the admin dashboard.
 */
export async function fetchAllCases(
  limit: number = 100,
  offset: number = 0,
): Promise<TaskPagedResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases?limit=${limit}&offset=${offset}`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy danh sách toàn bộ case: ${message}`);
  }
  const data = await res.json();
  return TaskPagedResponseSchema.parse(data);
}

/**
 * Pulls the list of cases assigned to the current advisor.
 */
export async function fetchAssignedCases(
  limit: number = 20,
  offset: number = 0,
): Promise<TaskPagedResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/assigned?limit=${limit}&offset=${offset}`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy danh sách case được giao: ${message}`);
  }
  const data = await res.json();
  return TaskPagedResponseSchema.parse(data);
}

/**
 * POST /cases/{case_id}/email/draft — trigger AI draft generation for one alert.
 */
export async function generateAiDraftForAlert(
  alert_id: string,
  case_id?: string | null,
): Promise<{ job_id?: string; status?: string }> {
  // If we have a case_id, use the standard case-based draft trigger
  if (case_id) {
    return generateAiDraft(case_id);
  }

  // Fallback logic for when we only have alert_id (sid)
  const requestBody = JSON.stringify({
    alert_id,
    case_id: case_id ?? undefined,
  });

  // The backend standard is /cases/{case_id}/email/draft
  // If case_id is missing, we try to use the alert_id as a temporary case_id
  // (though backend might fail if it's strictly expecting UUID and sid matches nothing in cases table)
  const primaryUrl = endpoint(
    `/cases/${encodeURIComponent(alert_id)}/email/draft`,
  );

  const executeDraftRequest = async (
    url: string,
  ): Promise<{ response: Response; raw: string; detail: string }> => {
    const response = await withTimeout(
      (signal) =>
        authFetch(
          url,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ booking_link: null }),
          },
          signal,
        ),
      DEFAULT_TIMEOUT_MS,
    );

    const raw = await response.text().catch(() => "");
    let detail: string = response.statusText;
    try {
      const parsed = raw ? JSON.parse(raw) : {};
      detail =
        (typeof parsed?.detail === "string" ? parsed.detail : "") ||
        (typeof parsed?.message === "string" ? parsed.message : "") ||
        detail;
    } catch {
      if (raw) detail = raw;
    }
    return { response, raw, detail };
  };

  const result = await executeDraftRequest(primaryUrl);
  if (result.response.ok) {
    return (result.raw ? JSON.parse(result.raw) : {}) as {
      job_id?: string;
      status?: string;
    };
  }

  throw new Error(
    `Không thể tạo nội dung email [${result.response.status}] (${primaryUrl}): ${result.detail}`,
  );
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
  const data = await res.json();
  return JobResultSchema.parse(data);
}

/**
 * PATCH /cases/{case_id}/email — update draft subject/body (UNAVAILABLE or DRAFT → DRAFT).
 * Must be called before sendNudge if no AI draft has been generated yet.
 */
export async function updateEmailDraft(
  case_id: string,
  payload: { subject?: string; body?: string },
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/${encodeURIComponent(case_id)}/email`),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    if (res.status === 400) {
      throw new Error("Nội dung và Tiêu đề Email không được để trống!");
    }
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Cập nhật nội dung email thất bại: ${message}`);
  }
}

/**
 * Send finalized email body to student.
 */
export async function sendNudge(
  case_id: string,
  payload: { body: string },
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/${encodeURIComponent(case_id)}/email/send`),
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
    throw new Error(`Gửi email thất bại: ${message}`);
  }
}

/**
 * GET /advisors/leaderboard[?time_window=...] — returns advisor leaderboard.
 */
export async function fetchAdvisorsLeaderboard(
  time_window?: "weekly" | "monthly" | "semester" | "all_time",
): Promise<AdvisorLeaderboard> {
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
  return AdvisorLeaderboardSchema.parse(data);
}

/**
 * GET /advisors/profile — returns current user's advisor profile.
 */
export async function fetchAdvisorProfile(): Promise<AdvisorProfileRead> {
  const res = await withTimeout(
    (signal) =>
      authFetch(endpoint("/advisors/profile"), { method: "GET" }, signal),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy thông tin hồ sơ: ${message}`);
  }
  const data = await res.json();
  return AdvisorProfileReadSchema.parse(data);
}

/**
 * GET /advisors/me/points — returns current user's advisor points.
 */
export async function fetchAdvisorPoints(): Promise<AdvisorPoints> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/advisors/me/points"),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy điểm thưởng: ${message}`);
  }
  const data = await res.json();
  return AdvisorPointsSchema.parse(data);
}

/**
 * PATCH /advisors/profile — updates current user's advisor profile.
 */
export async function updateAdvisorProfile(
  payload: AdvisorProfileUpdate,
): Promise<AdvisorProfileRead> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint("/advisors/profile"),
        {
          method: "PATCH",
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
    throw new Error(`Cập nhật hồ sơ thất bại: ${message}`);
  }
  const data = await res.json();
  return AdvisorProfileReadSchema.parse(data);
}

/**
 * GET /advisors/me/schedule — returns current user's schedule.
 */
export async function fetchAdvisorSchedule(): Promise<AdvisorScheduleRead> {
  const res = await withTimeout(
    (signal) =>
      authFetch(endpoint("/advisors/me/schedule"), { method: "GET" }, signal),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Lỗi tải lịch: ${res.statusText}`);
  }
  const data = await res.json();
  return AdvisorScheduleReadSchema.parse(data);
}

/**
 * POST /advisors/{advisor_id}/working-hours
 */
export async function addWorkingHours(
  advisor_id: string,
  payload: WorkingHoursCreate,
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/advisors/${encodeURIComponent(advisor_id)}/working-hours`),
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
    throw new Error(errorBody.detail || `Lỗi thêm giờ: ${res.statusText}`);
  }
}

/**
 * PUT /advisors/working-hours/{wh_id}
 */
export async function updateWorkingHours(
  wh_id: string,
  payload: WorkingHoursUpdate,
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/advisors/working-hours/${encodeURIComponent(wh_id)}`),
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Lỗi cập nhật giờ: ${res.statusText}`);
  }
}

/**
 * DELETE /advisors/working-hours/{wh_id}
 */
export async function deleteWorkingHours(wh_id: string): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/advisors/working-hours/${encodeURIComponent(wh_id)}`),
        { method: "DELETE" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Lỗi xoá giờ: ${res.statusText}`);
  }
}

/**
 * POST /advisors/{advisor_id}/days-off
 */
export async function addDayOff(
  advisor_id: string,
  payload: DayOffCreate,
): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/advisors/${encodeURIComponent(advisor_id)}/days-off`),
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
    throw new Error(errorBody.detail || `Lỗi thêm ngày nghỉ: ${res.statusText}`);
  }
}

/**
 * DELETE /advisors/days-off/{do_id}
 */
export async function deleteDayOff(do_id: string): Promise<void> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/advisors/days-off/${encodeURIComponent(do_id)}`),
        { method: "DELETE" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Lỗi xoá ngày nghỉ: ${res.statusText}`);
  }
}

/**
 * GET /metrics/stats — returns high-level dashboard KPIs.
 */
export async function fetchKpiStats(): Promise<KpiStats> {
  const res = await withTimeout(
    (signal) =>
      authFetch(endpoint("/metrics/stats"), { method: "GET" }, signal),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy chỉ số KPI: ${message}`);
  }
  const data = await res.json();
  return KpiStatsSchema.parse(data);
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
  return z.array(RetentionTrendItemSchema).parse(data);
}

/**
 * GET /cases/{case_id}/email — returns the intervention email for a case.
 */
export async function fetchCaseEmail(
  case_id: string,
): Promise<EmailHistoryItem | null> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/${encodeURIComponent(case_id)}/email`),
        { method: "GET" },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể lấy email của case: ${message}`);
  }
  const data = await res.json();
  if (!data) return null;
  return EmailHistoryItemSchema.parse(data);
}

/**
 * GET /cases/{case_id}/email — returns current draft status and content.
 */
export async function fetchDraftStatus(
  case_id: string,
): Promise<DraftStatusResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/${encodeURIComponent(case_id)}/email`),
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
  const data = await res.json();
  return DraftStatusResponseSchema.parse(data);
}

/**
 * GET /cases/{case_id} — returns full details for a case.
 */
export async function fetchCaseDetails(
  case_id: string,
): Promise<CaseDetailsResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/${encodeURIComponent(case_id)}`),
        {
          method: "GET",
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    throw new Error(`Không thể lấy chi tiết case: ${res.status}`);
  }
  const data = await res.json();
  return CaseDetailsResponseSchema.parse(data);
}

/**
 * POST /cases/{case_id}/email/draft — trigger async draft generation.
 */
export async function generateAiDraft(
  case_id: string,
  booking_link?: string,
): Promise<DraftJobResponse> {
  const res = await withTimeout(
    (signal) =>
      authFetch(
        endpoint(`/cases/${encodeURIComponent(case_id)}/email/draft`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ booking_link }),
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || res.statusText;
    throw new Error(`Không thể tạo bản nháp AI: ${message}`);
  }
  const data = await res.json();
  return DraftJobResponseSchema.parse(data);
}

/**
 * POST /cases/{case_id}/accept — an advisor accepts to solve a case.
 */
export async function acceptCase(case_id: string): Promise<void> {
  const trimmedCaseId = case_id.trim();
  if (!z.string().uuid().safeParse(trimmedCaseId).success) {
    throw new Error("Mã case không hợp lệ.");
  }

  const primaryUrl = endpoint(
    `/cases/${encodeURIComponent(trimmedCaseId)}/accept`,
  );
  const trailingSlashUrl = `${primaryUrl}/`;
  const candidateUrls = [primaryUrl, trailingSlashUrl];

  let lastError: {
    response?: Response;
    url: string;
    body: string;
    detail: string;
  } | null = null;

  for (const url of candidateUrls) {
    const res = await withTimeout(
      (signal) => authFetch(url, { method: "POST" }, signal),
      DEFAULT_TIMEOUT_MS,
    );
    if (res.ok) return;

    const body = await res.text().catch(() => "");
    let detail = res.statusText;
    try {
      const parsed = body ? JSON.parse(body) : {};
      detail =
        (typeof parsed?.detail === "string" ? parsed.detail : "") ||
        (typeof parsed?.message === "string" ? parsed.message : "") ||
        detail;
    } catch {
      if (body) detail = body;
    }

    lastError = { response: res, url, body, detail };
    if (res.status !== 404) break;
  }

  if (!lastError) {
    throw new Error("Không thể nhận case.");
  }

  throw new Error(
    `Không thể nhận case [${lastError.response?.status ?? "?"}] (${lastError.url}): ${lastError.detail}`,
  );
}

export type MeetingMethod = "online" | "in_person";

export type ConfirmBookingPayload = {
  /** ISO 8601 datetime with timezone offset, e.g. "2026-05-15T09:30:00+07:00". */
  appointmentTime: string;
  meetingMethod: MeetingMethod;
  notes?: string | null;
};

/**
 * POST /cases/{case_id}/book — student confirms appointment booking.
 * Public endpoint (no auth required) — called from /booking page.
 */
export async function confirmBooking(
  case_id: string,
  payload: ConfirmBookingPayload,
): Promise<void> {
  const trimmedCaseId = case_id.trim();
  if (!z.string().uuid().safeParse(trimmedCaseId).success) {
    throw new Error("Mã case không hợp lệ.");
  }
  const url = endpoint(`/cases/${encodeURIComponent(trimmedCaseId)}/book`);
  const requestBody = JSON.stringify({
    appointment_time: payload.appointmentTime,
    meeting_method: payload.meetingMethod,
    notes: payload.notes ?? "null",
  });
  console.log(requestBody);
  const res = await withTimeout(
    (signal) =>
      authFetch(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: requestBody,
          suppressUnauthorizedEvent: true,
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (res.ok) return;

  if (res.status === 409) {
    throw new SlotTakenError();
  }

  const body = await res.text().catch(() => "");
  let detail = res.statusText;
  try {
    const parsed = body ? JSON.parse(body) : {};
    detail =
      (typeof parsed?.detail === "string" ? parsed.detail : "") ||
      (typeof parsed?.message === "string" ? parsed.message : "") ||
      detail;
  } catch {
    if (body) detail = body;
  }
  throw new Error(`Xác nhận đặt lịch thất bại [${res.status}]: ${detail}`);
}

/**
 * POST /cases/{case_id}/supporting — advisor starts the supporting session
 * (BOOKED → SUPPORTING). Requires advisor auth.
 */
export async function startSupporting(case_id: string): Promise<void> {
  const trimmed = case_id.trim();
  if (!z.string().uuid().safeParse(trimmed).success) {
    throw new Error("Mã case không hợp lệ.");
  }
  const url = endpoint(`/cases/${encodeURIComponent(trimmed)}/supporting`);
  const res = await withTimeout(
    (signal) =>
      authFetch(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (res.ok) return;
  const body = await res.text().catch(() => "");
  let detail = res.statusText;
  try {
    const parsed = body ? JSON.parse(body) : {};
    detail =
      (typeof parsed?.detail === "string" ? parsed.detail : "") ||
      (typeof parsed?.message === "string" ? parsed.message : "") ||
      detail;
  } catch {
    if (body) detail = body;
  }
  throw new Error(`Bắt đầu hỗ trợ thất bại [${res.status}]: ${detail}`);
}

/**
 * POST /cases/{case_id}/resolve — advisor closes the case
 * (SUPPORTING → RESOLVED). Requires advisor auth.
 */
export async function resolveCase(case_id: string): Promise<void> {
  const trimmed = case_id.trim();
  if (!z.string().uuid().safeParse(trimmed).success) {
    throw new Error("Mã case không hợp lệ.");
  }
  const url = endpoint(`/cases/${encodeURIComponent(trimmed)}/resolve`);
  const res = await withTimeout(
    (signal) =>
      authFetch(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (res.ok) return;
  const body = await res.text().catch(() => "");
  let detail = res.statusText;
  try {
    const parsed = body ? JSON.parse(body) : {};
    detail =
      (typeof parsed?.detail === "string" ? parsed.detail : "") ||
      (typeof parsed?.message === "string" ? parsed.message : "") ||
      detail;
  } catch {
    if (body) detail = body;
  }
  throw new Error(`Giải quyết case thất bại [${res.status}]: ${detail}`);
}

export type StudentSatisfaction =
  | "very_bad"
  | "bad"
  | "normal"
  | "good"
  | "very_good";

/**
 * POST /cases/review?token=<JWT> — student submits satisfaction + comment.
 * Public endpoint. Backend verifies JWT and extracts case_id from it.
 */
export async function submitFeedback(
  token: string,
  satisfaction: StudentSatisfaction,
  comment: string | null,
): Promise<void> {
  const url = `${endpoint("/cases/review")}?token=${encodeURIComponent(token)}`;
  const res = await withTimeout(
    (signal) =>
      authFetch(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            satisfaction,
            comment: comment || null,
          }),
          suppressUnauthorizedEvent: true,
        },
        signal,
      ),
    DEFAULT_TIMEOUT_MS,
  );
  if (res.ok) return;
  const body = await res.text().catch(() => "");
  let detail = res.statusText;
  try {
    const parsed = body ? JSON.parse(body) : {};
    detail =
      (typeof parsed?.detail === "string" ? parsed.detail : "") ||
      (typeof parsed?.message === "string" ? parsed.message : "") ||
      detail;
  } catch {
    if (body) detail = body;
  }
  throw new Error(`Gửi đánh giá thất bại [${res.status}]: ${detail}`);
}

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
