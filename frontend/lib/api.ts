import { z } from "zod";

export class SlotTakenError extends Error {
  code = "SLOT_TAKEN" as const;
  constructor(message = "slot_taken") {
    super(message);
    this.name = "SlotTakenError";
  }
}

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
  "notified",
  "booked",
  "sent",
  "supporting",
  "pending_review",
  "failed",
  "resolved",
  "dismissed",
  "expired",
]);
export type BackendInterventionStatus = z.infer<
  typeof BackendInterventionStatusSchema
>;

export const RiskStatusSchema = z.enum([
  "Normal",
  "Elevated",
  "Critical",
  "Unknown",
]);
export type RiskStatus = z.infer<typeof RiskStatusSchema>;

export const StudentDTOSchema = z.object({
  sid: z.string(),
  student_name: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  major: z.string(),
  current_risk_status: RiskStatusSchema,
  intervention_status: BackendInterventionStatusSchema.nullable().optional(),
  last_notified_at: z.string().nullable().optional(),
  is_generating: z.boolean().default(false),
  active_case_id: z.string().nullable().optional(),
});
export type StudentDTO = z.infer<typeof StudentDTOSchema>;
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
  ai_overview: z
    .object({
      academic_summary: z.string().nullable().optional(),
      action_keys: z.array(z.string()).nullable().optional(),
    })
    .nullable()
    .optional(),
});

export const TaskItemSchema = TaskItemBaseSchema.transform((data) => {
  let emailStr = "";
  let draft_subject = null;
  let draft_body = null;
  let draft_status = null;
  let sent_at = null;

  if (data.email && typeof data.email === "object") {
    emailStr = data.email.recipent || data.email.recipient || "";
    draft_subject = data.email.subject || null;
    draft_body = data.email.body || null;
    draft_status = data.email.status || null;
    sent_at = data.email.sent_at || null;
  } else if (typeof data.email === "string") {
    emailStr = data.email;
  }

  return {
    ...data,
    email: emailStr,
    draft_subject,
    draft_body,
    draft_status,
    sent_at,
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

const BackendIngestRowSchema = z.object({
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
type BackendIngestRow = z.infer<typeof BackendIngestRowSchema>;

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

const CaseResponseSchema = z.object({
  case_id: z.string(),
  sid: z.string(),
  status: z.string(),
  created_at: z.string(),
  resolved_at: z.string().nullable().optional(),
});
type CaseResponse = z.infer<typeof CaseResponseSchema>;

const EmailHistoryItemSchema = z.object({
  email_id: z.string(),
  subject: z.string(),
  body: z.string(),
  status: z.enum(["generating", "draft", "sent"]),
  created_at: z.string(),
  sent_at: z.string().nullable(),
});
type EmailHistoryItem = z.infer<typeof EmailHistoryItemSchema>;


const CaseDetailsResponseSchema = CaseResponseSchema.extend({
  email: EmailHistoryItemSchema.nullable().optional(),
  appointment: AppointmentSchema.nullable().optional(),
});
type CaseDetailsResponse = z.infer<typeof CaseDetailsResponseSchema>;

const DraftJobResponseSchema = z.object({
  job_id: z.string(),
  status: z.string(),
});
type DraftJobResponse = z.infer<typeof DraftJobResponseSchema>;

const AdvisorLeaderboardItemSchema = z.object({
  advisor_id: z.string(),
  name: z.string(),
  total_points: z.number(),
  actions_count: z.number(),
  sent_count: z.number(),
  resolved_count: z.number(),
});
type AdvisorLeaderboardItem = z.infer<
  typeof AdvisorLeaderboardItemSchema
>;

const AdvisorLeaderboardSchema = z.object({
  items: z.array(AdvisorLeaderboardItemSchema),
  metadata: z.object({
    total_count: z.number().int().gte(0),
    limit: z.number().int().gte(0),
    offset: z.number().int().gte(0),
    has_next: z.boolean(),
  }),
});
type AdvisorLeaderboard = z.infer<typeof AdvisorLeaderboardSchema>;

export const UserReadSchema = z.object({
  id: z.string(),
  email: z.string(),
  role: z.enum(["admin", "advisor", "viewer"]).optional(),
});
export type UserRead = z.infer<typeof UserReadSchema>;

export const UserSettingsSchema = z.object({
  auto_draft_enabled: z.boolean(),
  ai_tone: z.string(),
  signature: z.string().nullable(),
  safety_rules: z.array(z.string()),
});
export type UserSettings = z.infer<typeof UserSettingsSchema>;

const AdvisorPointsSchema = z.object({
  points: z.number().int(),
});
type AdvisorPoints = z.infer<typeof AdvisorPointsSchema>;

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

const WorkingHoursReadSchema = z.object({
  id: z.string(),
  day_of_week: z.number(),
  start_time: z.string(), // "HH:MM:SS"
  end_time: z.string(),
  timezone: z.string(),
});
type WorkingHoursRead = z.infer<typeof WorkingHoursReadSchema>;

const DayOffReadSchema = z.object({
  id: z.string(),
  date: z.string(), // "YYYY-MM-DD"
  reason: z.string().nullable().optional(),
});
type DayOffRead = z.infer<typeof DayOffReadSchema>;

export const AdvisorScheduleReadSchema = z.object({
  working_hours: z.array(WorkingHoursReadSchema),
  days_off: z.array(DayOffReadSchema),
});
export type AdvisorScheduleRead = z.infer<typeof AdvisorScheduleReadSchema>;

const WorkingHoursCreateSchema = z.object({
  day_of_week: z.number(),
  start_time: z.string(),
  end_time: z.string(),
  timezone: z.string().default("UTC"),
});
export type WorkingHoursCreate = z.infer<typeof WorkingHoursCreateSchema>;

const WorkingHoursUpdateSchema = z.object({
  day_of_week: z.number(),
  start_time: z.string(),
  end_time: z.string(),
  timezone: z.string(),
});
type WorkingHoursUpdate = z.infer<typeof WorkingHoursUpdateSchema>;

const DayOffCreateSchema = z.object({
  date: z.string(),
  reason: z.string().nullable().optional(),
});
export type DayOffCreate = z.infer<typeof DayOffCreateSchema>;


const KpiStatsSchema = z.object({
  retention_rate: z.number(),
  total_interventions: z.number(),
  advisor_engagement: z.number(),
  dropout_rate: z.number(),
  total_students: z.number(),
});
export type KpiStats = z.infer<typeof KpiStatsSchema>;

const RetentionTrendItemSchema = z.object({
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

const DraftStatusResponseSchema = _QueryEmailDTOSchema.transform(
  (d) => ({
    subject: d.subject ?? null,
    body: d.body ?? null,
    is_generating: d.status === "generating",
    status: d.status,
  }),
);
type DraftStatusResponse = z.infer<typeof DraftStatusResponseSchema>;

/* ----------------------------------------------------------------------- */
/*  Configuration                                                          */
/* ----------------------------------------------------------------------- */

export const DEFAULT_TIMEOUT_MS = 10_000;
const INGEST_TIMEOUT_MS = 60_000;


// function getApiBase(): string {
//   // On the client, we MUST use the relative proxy path so that proxy.ts can
//   // intercept the request, extract the httpOnly cookie, and inject the Bearer token.
//   if (typeof window !== "undefined") {
//     return "/api/v1";
//   }

export function getApiBase(): string {
  // Lấy giá trị từ biến môi trường đã cấu hình trên Vercel
  const envBase = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;

  if (typeof window !== "undefined") {
    // ALWAYS use the relative path on the client.
    // This ensures requests go through proxy.ts for token injection
    // and next.config.mjs for rewrites to the backend.
    return "/api/v1";
  }

  // Cấu hình cho Server-side (giữ nguyên hoặc tối ưu)
  if (envBase && envBase.trim()) {
    return envBase.trim().replace(/\/+$/, "");
  }

  if (process.env.NODE_ENV === "production") {
    throw new Error("CRITICAL: NEXT_PUBLIC_API_BASE_URL is not set in production!");
  }

  return "http://127.0.0.1:8000/api/v1";
}

export function getWsUrl(token?: string | null): string {
  // Explicit WS URL has highest priority
  let wsUrl = process.env.NEXT_PUBLIC_WS_URL
    ? process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "")
    : "";

  if (!wsUrl) {
    const base = getApiBase();

    // If getApiBase returns a relative path (client-side), build absolute WS URL from window.location
    if (!base.startsWith("http")) {
      if (typeof window === "undefined") {
        // Server-side fallback if somehow called there without an absolute base
        wsUrl = "ws://127.0.0.1:8000/api/v1/ws";
      } else {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = window.location.host;
        // base is likely "/api/v1"
        wsUrl = `${protocol}//${host}${base.replace(/\/+$/, "")}/ws`;
      }
    } else {
      // If base is absolute, just swap http -> ws
      wsUrl = base.replace(/^http/, "ws").replace(/\/+$/, "") + "/ws";
    }
  }

  // Append token if provided
  if (token) {
    const url = new URL(wsUrl);
    url.searchParams.set("token", token);
    return url.toString();
  }

  return wsUrl;
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
async function getAuthToken(): Promise<string | null> {
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

  // On the server, inject via Cookie header (backend uses CookieTransport, not Bearer).
  // On the client, middleware reads the httpOnly cookie and injects Authorization header
  // before the rewrite to the real backend — client JS never sees the token.
  if (typeof window === "undefined") {
    const token = await getAuthToken();
    if (token) {
      headers.set("Cookie", `nexusedu_auth_token=${token}`);
    }
  }

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

// Reads the error detail string from a non-ok Response body.
// Tries JSON first (FastAPI returns { detail } or { message }), falls back to raw text.
async function parseErrorDetail(res: Response): Promise<string> {
  const body = await res.text().catch(() => "");
  try {
    const parsed = body ? JSON.parse(body) : {};
    return (
      (typeof parsed?.detail === "string" ? parsed.detail : "") ||
      (typeof parsed?.message === "string" ? parsed.message : "") ||
      body ||
      res.statusText
    );
  } catch {
    return body || res.statusText;
  }
}

// Standard fetch-parse-validate for endpoints that return JSON conforming to a Zod schema.
// Leave special cases (null-on-401, SlotTakenError, retry loops, void responses) handcoded.
// Uses z.ZodTypeAny + z.output<S> so transform schemas (ZodEffects) infer correctly.
async function apiCall<S extends z.ZodTypeAny>(
  url: string,
  init: RequestInit,
  schema: S,
  errorPrefix: string,
  timeout = DEFAULT_TIMEOUT_MS,
): Promise<z.output<S>> {
  const res = await withTimeout(
    (signal) => authFetch(url, init, signal),
    timeout,
  );
  if (!res.ok) {
    const detail = await parseErrorDetail(res);
    throw new Error(`${errorPrefix}: ${detail}`);
  }
  const data = await res.json();
  return schema.parse(data);
}

/* ----------------------------------------------------------------------- */
/*  Auth API: register / login / me                                         */
/* ----------------------------------------------------------------------- */

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
  return apiCall(
    endpoint("/users/me/settings"),
    { method: "GET" },
    UserSettingsSchema,
    "Failed to fetch user settings",
  );
}

/**
 * PATCH /users/me/settings — updates current user settings.
 */
export async function updateUserSettings(
  settings: Partial<UserSettings>,
): Promise<UserSettings> {
  return apiCall(
    endpoint("/users/me/settings"),
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    },
    UserSettingsSchema,
    "Failed to update user settings",
  );
}

/* ----------------------------------------------------------------------- */
/*  Public API                                                             */
/* ----------------------------------------------------------------------- */

export const ResponseKpiMetricSchema = z.object({
  avg_response_hours: z.number().nonnegative(),
  target_hours: z.number().nonnegative().default(4.0),
  within_kpi_rate: z.number().min(0).max(1),
  sla_breach_count: z.number().int().nonnegative(),
});

export const RecoveryMetricSchema = z.object({
  recovery_rate: z.number(),
  stabilized_students: z.number().int(),
  total_risk_students: z.number().int(),
  avg_recovery_days: z.number(),
});

export const ImpactHistorySchema = z.object({
  week: z.number().int().positive(),
  xp: z.number().int().nonnegative(),
});

export const ImpactMetricSchema = z.object({
  current_xp: z.number().int(),
  completion_rate: z.number(),
  ranking_position: z.number().int().nullable().optional(),
  month: z.number().int().positive(),
  year: z.number().int().positive(),
  weekly_history: z.array(ImpactHistorySchema),
});

export const EmergencyDashboardSchema = z.object({
  priority_queue: z.number().int().nonnegative(),
  response_kpi: ResponseKpiMetricSchema,
  activation: z.number().min(0).max(1),
  recovery: RecoveryMetricSchema,
  impact: ImpactMetricSchema,
});

export type EmergencyDashboard = z.infer<typeof EmergencyDashboardSchema>;

/**
 * GET /advisors/me/dashboard — returns the current advisor's dashboard metrics.
 */
export async function fetchAdvisorDashboard(): Promise<EmergencyDashboard> {
  return apiCall(
    endpoint("/advisors/me/dashboard"),
    { method: "GET" },
    EmergencyDashboardSchema,
    "Không thể lấy dữ liệu dashboard",
  );
}

/**
 * Sends multi-source data to the backend for ingestion.
 */
export async function ingestData(
  dataSources: {
    source_type: "sis" | "lms" | "custom";
    table_name?: string;
    records: any[];
  }[],
): Promise<{ job_id: string; status: string; batch_id: string }> {
  if (dataSources.length === 0) throw new Error("No data sources provided");
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
  return res.json();
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
  return apiCall(
    endpoint(`/cases/open?limit=${limit}&offset=${offset}`),
    { method: "GET" },
    TaskPagedResponseSchema,
    "Không thể lấy danh sách case đang mở",
  );
}

/**
 * Pulls the list of all cases for the admin dashboard.
 */
export async function fetchAllCases(
  limit: number = 100,
  offset: number = 0,
): Promise<TaskPagedResponse> {
  return apiCall(
    endpoint(`/cases?limit=${limit}&offset=${offset}`),
    { method: "GET" },
    TaskPagedResponseSchema,
    "Không thể lấy danh sách toàn bộ case",
  );
}

/**
 * Pulls the list of cases assigned to the current advisor.
 */
export async function fetchAssignedCases(
  limit: number = 20,
  offset: number = 0,
): Promise<TaskPagedResponse> {
  return apiCall(
    endpoint(`/cases/assigned?limit=${limit}&offset=${offset}`),
    { method: "GET" },
    TaskPagedResponseSchema,
    "Không thể lấy danh sách case được giao",
  );
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
    const res = await withTimeout(
      (signal) =>
        authFetch(
          endpoint(`/cases/${encodeURIComponent(case_id)}/email/draft`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
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
  return apiCall(
    endpoint(`/jobs/${encodeURIComponent(job_id)}`),
    { method: "GET" },
    JobResultSchema,
    "Kiểm tra trạng thái job thất bại",
  );
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
  return apiCall(
    endpoint(`/advisors/leaderboard${qp}`),
    { method: "GET" },
    AdvisorLeaderboardSchema,
    "Không thể lấy bảng xếp hạng",
  );
}

/**
 * GET /advisors/profile — returns current user's advisor profile.
 */
export async function fetchAdvisorProfile(): Promise<AdvisorProfileRead> {
  return apiCall(
    endpoint("/advisors/profile"),
    { method: "GET" },
    AdvisorProfileReadSchema,
    "Không thể lấy thông tin hồ sơ",
  );
}

/**
 * GET /advisors/me/points — returns current user's advisor points.
 */
export async function fetchAdvisorPoints(): Promise<AdvisorPoints> {
  return apiCall(
    endpoint("/advisors/me/points"),
    { method: "GET" },
    AdvisorPointsSchema,
    "Không thể lấy điểm thưởng",
  );
}

/**
 * PATCH /advisors/profile — updates current user's advisor profile.
 */
export async function updateAdvisorProfile(
  payload: AdvisorProfileUpdate,
): Promise<AdvisorProfileRead> {
  return apiCall(
    endpoint("/advisors/profile"),
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    AdvisorProfileReadSchema,
    "Cập nhật hồ sơ thất bại",
  );
}

/**
 * GET /advisors/me/schedule — returns current user's schedule.
 */
export async function fetchAdvisorSchedule(): Promise<AdvisorScheduleRead> {
  return apiCall(
    endpoint("/advisors/me/schedule"),
    { method: "GET" },
    AdvisorScheduleReadSchema,
    "Lỗi tải lịch",
  );
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

export const AdminDashboardSchema = z.object({
  recovery: z.object({
    recovery_rate: z.number().default(0),
    stabilized_students: z.number().int().default(0),
    total_at_risk_students: z.number().int().default(0),
  }).default({}),
  lead_time: z.object({
    avg_lead_time_hours: z.number().default(0),
    target_hours: z.number().default(4),
    within_target_rate: z.number().default(0),
  }).default({}),
  nudge_activation: z.object({
    activation_rate: z.number().default(0),
    total_nudges_sent: z.number().int().default(0),
    responses_received: z.number().int().default(0),
  }).default({}),
  academic_impact: z.object({
    avg_gpa_before: z.number().nullish().default(0),
    avg_gpa_after: z.number().nullish().default(0),
    impact_score: z.number().nullish().default(0),
  }).default({}),
  risk_distribution: z.array(z.object({
    label: z.string().default("Unknown"),
    count: z.number().int().default(0),
    percentage: z.number().default(0),
  })).default([]),
  major_risk: z.array(z.object({
    major: z.string().default("Unknown"),
    total_students: z.number().int().default(0),
    risk_percentage: z.number().default(0),
  })).default([]),
  systemic_risk: z.object({
    avg_breadth: z.number().default(0),
    systemic_case_count: z.number().int().default(0),
  }).nullish(),
  trend_distribution: z.object({
    improving: z.number().int().default(0),
    stable: z.number().int().default(0),
    declining: z.number().int().default(0),
  }).nullish(),
  generated_at: z.string().nullish().default(() => new Date().toISOString()),
});

export type AdminDashboardData = z.infer<typeof AdminDashboardSchema>;

/**
 * GET /admin/dashboard — returns high-level admin dashboard metrics.
 */
export async function fetchAdminDashboard(): Promise<AdminDashboardData> {
  return apiCall(
    endpoint("/admin/dashboard"),
    { method: "GET" },
    AdminDashboardSchema,
    "Không thể lấy dữ liệu dashboard admin",
  );
}

/**
 * GET /metrics/stats — returns high-level dashboard KPIs.
 */
export async function fetchKpiStats(): Promise<KpiStats> {
  return apiCall(
    endpoint("/metrics/stats"),
    { method: "GET" },
    KpiStatsSchema,
    "Không thể lấy chỉ số KPI",
  );
}

/**
 * GET /metrics/retention — returns retention trend data.
 */
export async function fetchRetentionTrend(): Promise<RetentionTrendItem[]> {
  return apiCall(
    endpoint("/metrics/retention"),
    { method: "GET" },
    z.array(RetentionTrendItemSchema),
    "Không thể lấy xu hướng giữ chân",
  );
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
  return apiCall(
    endpoint(`/cases/${encodeURIComponent(case_id)}/email`),
    { method: "GET" },
    DraftStatusResponseSchema,
    "Không thể lấy trạng thái bản nháp",
  );
}

/**
 * GET /cases/{case_id} — returns full details for a case.
 */
export async function fetchCaseDetails(
  case_id: string,
): Promise<CaseDetailsResponse> {
  return apiCall(
    endpoint(`/cases/${encodeURIComponent(case_id)}`),
    { method: "GET" },
    CaseDetailsResponseSchema,
    "Không thể lấy chi tiết case",
  );
}

export const StudentCourseSchema = z.object({
  course_name: z.string(),
  avg_score: z.number(),
});

export const StudentTermMetricsSchema = z.object({
  academic_year: z.number(),
  semester: z.number(),
  term_avg_score: z.number(),
  previous_terms_avg_score: z.number().nullable(),
  courses: z.array(StudentCourseSchema),
});

export const StudentMetricsResponseSchema = z.object({
  terms: z.array(StudentTermMetricsSchema),
});

export type StudentMetricsResponse = z.infer<typeof StudentMetricsResponseSchema>;


/**
 * GET /students/{sid}/metrics/terms — returns academic metrics by term.
 */
export async function fetchStudentMetrics(
  sid: string,
): Promise<StudentMetricsResponse> {
  return apiCall(
    endpoint(`/students/${encodeURIComponent(sid)}/metrics/terms`),
    { method: "GET" },
    StudentMetricsResponseSchema,
    "Không thể lấy dữ liệu học tập",
  );
}


/**
 * GET /students/{sid} — returns details for a specific student.
 */
export async function fetchStudent(sid: string): Promise<StudentDTO> {
  return apiCall(
    endpoint(`/students/${encodeURIComponent(sid)}`),
    { method: "GET" },
    StudentDTOSchema,
    "Không thể lấy thông tin sinh viên",
  );
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
    detail: string;
  } | null = null;

  for (const url of candidateUrls) {
    const res = await withTimeout(
      (signal) => authFetch(url, { method: "POST" }, signal),
      DEFAULT_TIMEOUT_MS,
    );
    if (res.ok) return;

    const detail = await parseErrorDetail(res);
    lastError = { response: res, url, detail };
    if (res.status !== 404) break;
  }

  if (!lastError) {
    throw new Error("Không thể nhận case.");
  }

  throw new Error(
    `Không thể nhận case [${lastError.response?.status ?? "?"}] (${lastError.url}): ${lastError.detail}`,
  );
}

type MeetingMethod = "online" | "in_person";

type ConfirmBookingPayload = {
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

  const detail = await parseErrorDetail(res);
  throw new Error(`Xác nhận đặt lịch thất bại [${res.status}]: ${detail}`);
}

export type TakenSlot = { start_time: string; end_time: string };

const TakenSlotSchema = z.object({
  start_time: z.string(),
  end_time: z.string(),
});

/**
 * GET /cases/{case_id}/taken-slots?date=YYYY-MM-DD
 * Public endpoint — no auth required.
 */
export async function fetchTakenSlots(
  case_id: string,
  date: string,
): Promise<TakenSlot[]> {
  const trimmed = case_id.trim();
  const url = `${endpoint(`/cases/${encodeURIComponent(trimmed)}/taken-slots`)}?date=${encodeURIComponent(date)}`;
  const res = await withTimeout(
    (signal) =>
      authFetch(url, { method: "GET", suppressUnauthorizedEvent: true }, signal),
    DEFAULT_TIMEOUT_MS,
  );
  if (!res.ok) return [];
  const json = await res.json();
  return z.array(TakenSlotSchema).parse(json);
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
  const detail = await parseErrorDetail(res);
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
  const detail = await parseErrorDetail(res);
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
  const detail = await parseErrorDetail(res);
  throw new Error(`Gửi đánh giá thất bại [${res.status}]: ${detail}`);
}
