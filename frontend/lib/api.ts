import { toast } from "sonner";
import { z } from "zod";

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

/* ----------------------------------------------------------------------- */
/*  Schemas & Types                                                        */
/* ----------------------------------------------------------------------- */

export const BackendInterventionStatusSchema = z.enum([
    "none",
    "notified",
    "sent",
    "booked",
    "supporting",
    "resolved",
    "dismissed",
    "expired",
]);
export type BackendInterventionStatus = z.infer<
    typeof BackendInterventionStatusSchema
>;

export const BackendRiskStatusSchema = z.string();
export type BackendRiskStatus = string;

export const BackendAlertSchema = z.object({
    sid: z.string(),
    student_name: z.string(),
    email: z.string(),
    current_risk_status: BackendRiskStatusSchema,
    intervention_status: BackendInterventionStatusSchema,
    is_generating: z.boolean().optional(),
    active_case_id: z.string().nullable().optional(),
});
export type BackendAlert = z.infer<typeof BackendAlertSchema>;

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
    status: z.enum(["draft", "sent"]),
    created_at: z.string(),
    sent_at: z.string().nullable(),
});
export type EmailHistoryItem = z.infer<typeof EmailHistoryItemSchema>;

export const CaseDetailsResponseSchema = CaseResponseSchema.extend({
    email: EmailHistoryItemSchema.nullable().optional(),
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

export const UserReadSchema = z.object({
    id: z.string(),
    email: z.string(),
    role: z.enum(["admin", "advisor", "viewer"]).optional(),
});
export type UserRead = z.infer<typeof UserReadSchema>;

export const AdvisorEngagementItemSchema = z.object({
    faculty: z.string(),
    sent: z.number(),
    drafted: z.number(),
});
export type AdvisorEngagementItem = z.infer<typeof AdvisorEngagementItemSchema>;

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


export const DraftStatusResponseSchema = z.object({
    sid: z.string(),
    is_generating: z.boolean(),
    progress: z.number().optional(),
    subject: z.string().nullable(),
    body: z.string().nullable(),
    active_case_id: z.string().nullable().optional(),
});
export type DraftStatusResponse = z.infer<typeof DraftStatusResponseSchema>;

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
    const env =
        typeof process !== "undefined"
            ? (process.env.NEXT_PUBLIC_API_BASE_URL as string | undefined)
            : undefined;

    if (env && env.trim()) {
        const base = env.trim().replace(/\/+$/, "");
        // If we're on the server and the base is relative, we need to make it absolute.
        // However, it's better to use a dedicated server-only env var or a known backend URL.
        if (typeof window === "undefined" && base.startsWith("/")) {
            // Fallback to localhost if we're in a relative proxy mode but on the server
            return `http://localhost:8000${base}`;
        }
        return base;
    }

    // Default to the documented base path.
    // On the server, we must use an absolute URL.
    if (typeof window === "undefined") {
        return "http://localhost:8000/api/v1";
    }

    return "/api/v1";
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
    opts: RequestInit = {},
    signal?: AbortSignal,
): Promise<Response> {
    const headers = new Headers(opts.headers || undefined);
    headers.set("Accept", headers.get("Accept") || "application/json");

    // On the server, we must manually inject the token from cookies
    if (typeof window === "undefined") {
        const token = await getAuthToken();
        if (token) {
            headers.set("Authorization", `Bearer ${token}`);
        }
    }
    // On the client, we rely on middleware to inject the token from the httpOnly cookie
    // for all requests to /api/v1/*

    const merged: RequestInit = {
        ...opts,
        headers,
        signal: opts.signal ?? signal,
    };

    const res = await fetch(url, merged);

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
        (signal) => authFetch(endpoint("/users/me"), { method: "GET" }, signal),
        DEFAULT_TIMEOUT_MS,
    );

    if (!res.ok) {
        if (res.status === 401) return null;
        const errorBody = await res.json().catch(() => ({}));
        throw new Error(
            errorBody.detail || `Failed to fetch user: ${res.status}`,
        );
    }

    const data = await res.json();
    return UserReadSchema.parse(data);
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
    return z.array(BackendAlertSchema).parse(data);
}

/**
 * Pushes a status transition for a single student.
 */
export async function updateAlertStatus(
    case_id: string,
    status: BackendInterventionStatus,
): Promise<void> {
    const res = await withTimeout(
        (signal) =>
            authFetch(
                endpoint(`/alerts/cases/${encodeURIComponent(case_id)}/status`),
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
    const data = await res.json();
    return JobResultSchema.parse(data);
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
                endpoint(`/alerts/cases/${encodeURIComponent(case_id)}/send`),
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
 * POST /query — ask the async AI agent for analysis.
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
    const data = await res.json();
    return DraftJobResponseSchema.parse(data);
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
    return z.array(AdvisorLeaderboardItemSchema).parse(data);
}

/**
 * GET /advisors/engagement — returns engagement metrics by faculty/major.
 */
export async function fetchAdvisorsEngagement(): Promise<
    AdvisorEngagementItem[]
> {
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
    return z.array(AdvisorEngagementItemSchema).parse(data);
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
 * GET /alerts/cases/{case_id}/email — returns the intervention email for a case.
 */
export async function fetchCaseEmail(
    case_id: string,
): Promise<EmailHistoryItem | null> {
    const res = await withTimeout(
        (signal) =>
            authFetch(
                endpoint(`/alerts/cases/${encodeURIComponent(case_id)}/email`),
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
 * GET /alerts/cases/{case_id}/draft — returns current draft status and content.
 */
export async function fetchDraftStatus(
    case_id: string,
): Promise<DraftStatusResponse> {
    const res = await withTimeout(
        (signal) =>
            authFetch(
                endpoint(`/alerts/cases/${encodeURIComponent(case_id)}/draft`),
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
 * GET /alerts/{sid}/cases — returns historical cases for a student.
 */
export async function fetchStudentCases(sid: string): Promise<CaseResponse[]> {
    const res = await withTimeout(
        (signal) =>
            authFetch(endpoint(`/alerts/${encodeURIComponent(sid)}/cases`), {
                method: "GET",
            }, signal),
        DEFAULT_TIMEOUT_MS,
    );
    if (!res.ok) {
        throw new Error(`Không thể lấy lịch sử case: ${res.status}`);
    }
    const data = await res.json();
    return z.array(CaseResponseSchema).parse(data);
}

/**
 * GET /alerts/cases/{case_id} — returns full details for a case.
 */
export async function fetchCaseDetails(case_id: string): Promise<CaseDetailsResponse> {
    const res = await withTimeout(
        (signal) =>
            authFetch(endpoint(`/alerts/cases/${encodeURIComponent(case_id)}`), {
                method: "GET",
            }, signal),
        DEFAULT_TIMEOUT_MS,
    );
    if (!res.ok) {
        throw new Error(`Không thể lấy chi tiết case: ${res.status}`);
    }
    const data = await res.json();
    return CaseDetailsResponseSchema.parse(data);
}

/**
 * POST /alerts/cases/{case_id}/draft — trigger async draft generation.
 */
export async function generateAiDraft(
    case_id: string,
    booking_link?: string,
): Promise<DraftJobResponse> {
    const res = await withTimeout(
        (signal) =>
            authFetch(
                endpoint(`/alerts/cases/${encodeURIComponent(case_id)}/draft`),
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
