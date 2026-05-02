/**
 * Centralized query keys for TanStack Query.
 * Using a consistent naming convention helps with debugging and manual cache invalidation.
 */
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  alerts: {
    all: ["alerts"] as const,
    list: () => [...queryKeys.alerts.all, "list"] as const,
    detail: (sid: string) => [...queryKeys.alerts.all, "detail", sid] as const,
    cases: (sid: string) => [...queryKeys.alerts.all, "detail", sid, "cases"] as const,
    caseDetail: (caseId: string) => [...queryKeys.alerts.all, "case", caseId] as const,
    draft: (sid: string) => [...queryKeys.alerts.all, sid, "draft"] as const,
  },
  schedule: {
    all: ["schedule"] as const,
  },
  metrics: {
    stats: ["metrics", "stats"] as const,
    retention: ["metrics", "retention"] as const,
  },
  advisors: {
    leaderboard: (window?: string) => ["advisors", "leaderboard", { window }] as const,
    engagement: () => ["advisors", "engagement"] as const,
  },
  jobs: {
    status: (jobId: string) => ["jobs", "status", jobId] as const,
  },
};
