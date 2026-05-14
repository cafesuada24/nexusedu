"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  type BackendInterventionStatus,
  fetchDraftStatus,
  fetchCaseDetails,
  fetchCaseEmail,
  fetchTasks,
  acceptCase,
  startSupporting,
  resolveCase,
  fetchOpenCases,
  fetchAssignedCases,
  fetchAllCases,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { toast } from "sonner";
import React from "react";

import { useAuth } from "@/hooks/use-auth";
import { getAllStudentConcerns } from "@/lib/awaiting-feedback";

/**
 * Hook to fetch the list of alerts (at-risk students).
 * Merges /alerts with /cases data to resolve active_case_id which is
 * currently hardcoded to null in the backend's /alerts query handler.
 */
export function useAlerts() {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: queryKeys.alerts.list(),
    queryFn: async () => {
      console.log(
        "[useAlerts] Fetching open and assigned cases...",
      );
      try {
        const [openRes, assignedRes] = await Promise.all([
          fetchOpenCases(100, 0),
          fetchAssignedCases(100, 0),
        ]);

        // Deduplicate by case_id to prevent duplicate keys if results overlap
        const seenCaseIds = new Set<string>();
        const allItems: any[] = [];

        for (const item of [...openRes.items, ...assignedRes.items]) {
          if (!seenCaseIds.has(item.case_id)) {
            seenCaseIds.add(item.case_id);
            allItems.push(item);
          }
        }

        const concerns = getAllStudentConcerns();

        const enriched = allItems.map((c) => ({
          sid: c.sid,
          student_name: c.student_name,
          email: c.email || "",
          current_risk_status: c.current_risk_status,
          intervention_status: c.intervention_status,
          student_concern: concerns[c.case_id] ?? null,
          active_case_id: c.case_id,
          case_id: c.case_id,
          assigned_advisor_id: c.assigned_advisor_id,
          assigned_to: c.assigned_to,
          draft_subject: c.draft_subject || null,
          draft_body: c.draft_body || null,
          draft_status: c.draft_status || null,
          is_generating: c.draft_status === "generating",
          appointment: c.appointment || null,
          created_at: c.created_at,
          sent_at: c.sent_at || null,
          ai_overview: c.ai_overview || null,
        }));

        console.log(
          "[useAlerts] Unified alerts from cases:",
          enriched.length,
        );
        return enriched;
      } catch (err) {
        console.error("[useAlerts] Fetch error:", err);
        throw err;
      }
    },
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 30000,
    retry: false,
  });
}

/**
 * Mutation hook to update an alert's intervention status.
 * Implements optimistic updates to ensure the Kanban board feels snappy.
 */
export function useUpdateAlertStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      case_id,
      status,
      isAccept,
    }: {
      case_id: string;
      status: BackendInterventionStatus;
      sid?: string;
      isAccept?: boolean;
    }) => {
      if (isAccept) {
        return acceptCase(case_id);
      }
      // Backend exposes one POST endpoint per transition rather than a
      // single PATCH /status. Dispatch based on the requested target.
      switch (status) {
        case "supporting":
          return startSupporting(case_id);
        case "resolved":
          // BE transitions SUPPORTING → PENDING_REVIEW and triggers
          // the worker to dispatch a feedback-request email. The
          // case is finalized to RESOLVED|FAILED only after the
          // student submits via POST /cases/review.
          return resolveCase(case_id);
        default:
          throw new Error(
            `Không hỗ trợ chuyển trạng thái sang "${status}" từ UI.`,
          );
      }
    },

    // Optimistic Update logic
    onMutate: async ({
      case_id,
      status,
      sid,
      isAccept,
    }: {
      case_id: string;
      status: BackendInterventionStatus;
      sid?: string;
      isAccept?: boolean;
    }) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({
        queryKey: queryKeys.alerts.list(),
      });

      // Snapshot the previous value
      const previousAlerts = queryClient.getQueryData(
        queryKeys.alerts.list(),
      );

      // Optimistically update to the new value. "resolved" click
      // triggers the BE review-request flow → status becomes
      // pending_review until the student submits feedback.
      const optimisticStatus =
        status === "resolved" ? "pending_review" : status;
      queryClient.setQueryData(
        queryKeys.alerts.list(),
        (old: any[] | undefined) => {
          if (!old) return [];
          return old.map((alert) =>
            alert.case_id === case_id || alert.sid === sid
              ? {
                ...alert,
                intervention_status: optimisticStatus,
                ...(isAccept
                  ? {
                    assigned_advisor_id: sid ?? case_id,
                    active_case_id:
                      alert.active_case_id ?? case_id,
                  }
                  : {}),
              }
              : alert,
          );
        },
      );

      // Return a context object with the snapshotted value
      return { previousAlerts };
    },

    // If the mutation fails, use the context returned from onMutate to roll back
    onError: (err, variables, context) => {
      if (context?.previousAlerts) {
        queryClient.setQueryData(
          queryKeys.alerts.list(),
          context.previousAlerts,
        );
      }
      const message =
        err instanceof Error && err.message
          ? err.message
          : "Vui lòng thử lại sau.";
      const notFound =
        message.includes("[404]") || /not found/i.test(message);
      const isAccept = variables.isAccept;

      toast.error(
        isAccept
          ? "Không thể nhận case"
          : "Không thể cập nhật trạng thái",
        {
          description: notFound
            ? "Không tìm thấy case hợp lệ cho sinh viên này. Vui lòng tải lại danh sách."
            : message,
        },
      );
    },

    // Show success feedback and refetch
    onSuccess: () => { },

    // Always refetch after error or success to ensure we are in sync with the server
    onSettled: async () => {
      // Small delay to allow background workers to process before the refetch
      // This helps prevent the "revert" jump in the UI.
      await new Promise((resolve) => setTimeout(resolve, 1000));
      queryClient.invalidateQueries({
        queryKey: queryKeys.alerts.list(),
      });
    },
  });
}

/**
 * Hook to poll draft status for a case.
 */
export function useDraftStatus(case_id?: string | null) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: case_id
      ? queryKeys.cases.draft(case_id)
      : ["cases", "draft", "none"],
    queryFn: async () => {
      if (!case_id) return null;
      return await fetchDraftStatus(case_id);
    },
    enabled: isAuthenticated && !!case_id,
    // Poll only if the query data suggests generation is in progress.
    refetchInterval: (query) => {
      const state = query.state;
      const data = state.data;

      // Stop polling if the fetch errored.
      if (state.error) return false;

      // If we have data and it says NOT generating, we can stop.
      if (data && !data.is_generating) return false;

      // Otherwise (no data yet or explicitly generating), poll every 30s as a fallback.
      return 30000;
    },
    // Prevent refetching on window focus to reduce noise during background polling.
    refetchOnWindowFocus: false,
    staleTime: 0,
    retry: 2,
    retryDelay: 3000,
  });
}

/**
 * Hook to fetch full details for a specific case.
 */
export function useCaseDetails(caseId: string) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.cases.detail(caseId),
    queryFn: () => fetchCaseDetails(caseId),
    enabled: isAuthenticated && !!caseId,
  });
}

/**
 * Hook to fetch the single email for a specific case.
 */
export function useCaseEmail(caseId: string) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: [...queryKeys.cases.all, "case", caseId, "email"],
    queryFn: () => fetchCaseEmail(caseId),
    enabled: isAuthenticated && !!caseId,
  });
}

/**
 * Hook to fetch the unified advisor task list.
 */
export function useTasks(limit: number = 20, offset: number = 0) {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.cases.tasks(), limit, offset],
    queryFn: () => fetchTasks(limit, offset),
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 10000,
  });
}

/**
 * Hook to fetch open (unassigned) cases for admin oversight.
 */
export function useOpenCases(limit: number = 100, offset: number = 0) {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.cases.all, "open", limit, offset],
    queryFn: () => fetchOpenCases(limit, offset),
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 10000,
  });
}

/**
 * Hook to fetch cases for admin oversight.
 */
export function useCases(limit: number = 100, offset: number = 0) {
  const { isAuthenticated } = useAuth();
  const [isMounted, setIsMounted] = React.useState(false);

  React.useEffect(() => {
    setIsMounted(true);
  }, []);

  return useQuery({
    queryKey: [...queryKeys.cases.all, limit, offset],
    queryFn: () => fetchAllCases(limit, offset),
    enabled: isMounted && isAuthenticated,
    refetchOnWindowFocus: true,
    refetchInterval: 10000,
  });
}
