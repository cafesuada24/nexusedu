"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    updateAlertStatus,
    type BackendInterventionStatus,
    fetchDraftStatus,
    fetchStudentCases,
    fetchCaseDetails,
    fetchCaseEmail,
    fetchTasks,
    fetchAlerts,
    acceptCase,
    fetchOpenCases,
    fetchAssignedCases,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { toast } from "sonner";
import React from "react";

import { useAuth } from "@/hooks/use-auth";

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
                "[useAlerts] Fetching all alerts and zipping case IDs...",
            );
            try {
                // 1. Fetch alerts (these have the students we care about)
                const alerts = await fetchAlerts();

                // 2. Fetch open and assigned cases to find their case_ids
                // We fetch a larger limit to ensure we catch most active cases
                const [openRes, assignedRes] = await Promise.all([
                    fetchOpenCases(100, 0),
                    fetchAssignedCases(100, 0),
                ]);

                // 3. Build a map of sid -> case details
                const caseMap: Record<
                    string,
                    {
                        case_id: string;
                        assigned_advisor_id?: string | null;
                        draft_subject?: string | null;
                        draft_body?: string | null;
                        draft_status?: string | null;
                    }
                > = {};
                [...openRes.items, ...assignedRes.items].forEach((c) => {
                    if (c.sid) {
                        caseMap[c.sid] = {
                            case_id: c.case_id,
                            assigned_advisor_id: c.assigned_advisor_id,
                            draft_subject: c.draft_subject,
                            draft_body: c.draft_body,
                            draft_status: c.draft_status,
                        };
                    }
                });

                // 4. Zip the data
                const enriched = alerts.map((a) => {
                    const c = caseMap[a.sid];
                    return {
                        ...a,
                        active_case_id: a.active_case_id || c?.case_id || null,
                        assigned_advisor_id:
                            a.assigned_advisor_id ||
                            c?.assigned_advisor_id ||
                            null,
                        draft_subject:
                            a.draft_subject || c?.draft_subject || null,
                        draft_body: a.draft_body || c?.draft_body || null,
                        draft_status: a.draft_status || c?.draft_status || null,
                    };
                });

                console.log(
                    "[useAlerts] Enriched alerts with case IDs:",
                    enriched.length,
                );
                return enriched;
            } catch (err) {
                console.error("[useAlerts] Enrichment error:", err);
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
            return updateAlertStatus(case_id, status);
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

            // Optimistically update to the new value
            queryClient.setQueryData(
                queryKeys.alerts.list(),
                (old: any[] | undefined) => {
                    if (!old) return [];
                    return old.map((alert) =>
                        alert.case_id === case_id || alert.sid === sid
                            ? {
                                  ...alert,
                                  intervention_status: status,
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
