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
  },
  cases: {
    all: ["cases"] as const,
    tasks: () => [...queryKeys.cases.all, "tasks"] as const,
    detail: (caseId: string) => [...queryKeys.cases.all, "detail", caseId] as const,
    draft: (caseId: string) => [...queryKeys.cases.all, "draft", caseId] as const,
  },
  schedule: {
    all: ["schedule"] as const,
  },
  appointments: {
    all: ["appointments"] as const,
    list: (caseId: string, from: string, to: string) =>
      ["appointments", "list", caseId, from, to] as const,
  },
  metrics: {
    stats: ["metrics", "stats"] as const,
    retention: ["metrics", "retention"] as const,
  },
  advisors: {
    leaderboard: (window?: string) => ["advisors", "leaderboard", { window }] as const,
  },
  jobs: {
    status: (jobId: string) => ["jobs", "status", jobId] as const,
  },
};
