"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    type BackendInterventionStatus,
    fetchDraftStatus,
    fetchStudentCases,
    fetchCaseDetails,
    fetchCaseEmail,
    fetchTasks,
    acceptCase,
    startSupporting,
    fetchOpenCases,
    fetchAssignedCases,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { toast } from "sonner";
import React from "react";

import { useAuth } from "@/hooks/use-auth";
import {
    getAwaitingFeedbackSet,
    getAllStudentConcerns,
    markAwaitingFeedback,
} from "@/lib/awaiting-feedback";
import type { Appointment } from "@/lib/appointments";

const PRE_BOOKED_STATUSES = new Set(["new", "accepted", "sent"]);

async function fetchAppointments(): Promise<Appointment[]> {
    try {
        const res = await fetch("/api/appointments", { cache: "no-store" });
        if (!res.ok) return [];
        return (await res.json()) as Appointment[];
    } catch {
        return [];
    }
}

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
                // Fetch open and assigned cases + appointments in parallel
                const [openRes, assignedRes, appointments] = await Promise.all([
                    fetchOpenCases(100, 0),
                    fetchAssignedCases(100, 0),
                    fetchAppointments(),
                ]);

                const allItems = [...openRes.items, ...assignedRes.items];

                // Frontend override: cases marked locally as awaiting feedback
                // are displayed in "Đang hỗ trợ" with the awaiting badge,
                // regardless of the backend's current intervention_status.
                const awaitingSet = getAwaitingFeedbackSet();
                const concerns = getAllStudentConcerns();
                const bookedCaseIds = new Set(
                    appointments.map((a) => a.caseId),
                );

                // Map cases to the unified alert shape expected by the UI
                const enriched = allItems.map((c) => {
                    const backendStatus = (
                        c.intervention_status || ""
                    ).toLowerCase();
                    // If the student has booked a slot via /api/appointments,
                    // surface the case as "booked" — but only when the backend
                    // hasn't already moved past BOOKED (supporting / resolved
                    // / awaiting_feedback take precedence).
                    const appointmentOverride =
                        bookedCaseIds.has(c.case_id) &&
                        PRE_BOOKED_STATUSES.has(backendStatus)
                            ? "booked"
                            : null;

                    return {
                        sid: c.sid,
                        student_name: c.student_name,
                        email: c.email || "",
                        current_risk_status: c.current_risk_status,
                        intervention_status: awaitingSet.has(c.case_id)
                            ? "awaiting_feedback"
                            : (appointmentOverride ?? c.intervention_status),
                        student_concern: concerns[c.case_id] ?? null,
                        active_case_id: c.case_id,
                        case_id: c.case_id,
                        assigned_advisor_id: c.assigned_advisor_id,
                        assigned_to: c.assigned_to,
                        draft_subject: c.draft_subject || null,
                        draft_body: c.draft_body || null,
                        draft_status: c.draft_status || null,
                        is_generating: c.draft_status === "generating",
                    };
                });

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
        refetchInterval: 10000,
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
                    // Frontend-only flow until backend supports
                    // AWAITING_FEEDBACK: don't call resolveCase (which would
                    // immediately set RESOLVED). Just persist the local
                    // override; student submitting feedback will trigger the
                    // real resolve when backend is ready.
                    markAwaitingFeedback(case_id);
                    return Promise.resolve();
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

            // Optimistically update to the new value.
            // "resolved" click triggers the feedback-request flow — card stays
            // in "Đang hỗ trợ" and shows "Chờ sinh viên đánh giá" badge.
            const optimisticStatus =
                status === "resolved" ? "awaiting_feedback" : status;
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
        onSuccess: () => {},

        // Always refetch after error or success to ensure we are in sync with the server
        onSettled: () => {
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

            // Otherwise (no data yet or explicitly generating), poll every 5s.
            return 5000;
        },
        // Prevent refetching on window focus to reduce noise during background polling.
        refetchOnWindowFocus: false,
        staleTime: 0,
        retry: 2,
        retryDelay: 3000,
    });
}

/**
 * Hook to fetch all historical cases for a student.
 */
export function useStudentCases(sid: string) {
    const { isAuthenticated } = useAuth();
    return useQuery({
        queryKey: queryKeys.cases.student(sid),
        queryFn: () => fetchStudentCases(sid),
        enabled: isAuthenticated && !!sid,
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
