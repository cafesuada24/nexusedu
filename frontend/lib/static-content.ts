/**
 * Static content seam — data that is currently hardcoded but should
 * eventually come from backend API endpoints.
 *
 * TODO(backend): replace ADVISOR_META with GET /advisors/{token} once
 * the endpoint exists, so new advisors can be added without a redeploy.
 */

export type AdvisorMeta = {
  advisor: string;
  role: string;
};

export const ADVISOR_META: Record<string, AdvisorMeta> = {
  "le-ha": {
    advisor: "TS. Lê Hà",
    role: "Cố vấn học tập · Khoa CNTT",
  },
};

export const DEFAULT_ADVISOR_META: AdvisorMeta = {
  advisor: "Cố vấn học tập",
  role: "NexusEdu",
};
