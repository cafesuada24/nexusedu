"use client";

import React, { createContext, useContext, useEffect } from "react";
import { useWebSocket, WebSocketMessage } from "@/hooks/use-websocket";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { fetchDraftStatus } from "@/lib/api";
import { toast } from "sonner";

interface WebSocketContextType {
    status: "connecting" | "open" | "closed";
}

const WebSocketContext = createContext<WebSocketContextType>({
    status: "closed",
});

export const useWebSocketContext = () => useContext(WebSocketContext);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
    const queryClient = useQueryClient();
    const getCaseIdFromJobPayload = React.useCallback((rawPayload: unknown) => {
        const payload = (rawPayload ?? {}) as Record<string, any>;
        const metadataCaseId = payload.metadata?.case_id;
        if (typeof metadataCaseId === "string" && metadataCaseId) {
            return metadataCaseId;
        }
        const correlationId = payload.correlation_id;
        if (typeof correlationId === "string" && correlationId) {
            return correlationId;
        }
        return null;
    }, []);

    const getJobType = React.useCallback((rawPayload: unknown) => {
        const payload = (rawPayload ?? {}) as Record<string, any>;
        const jobType = payload.job_type ?? payload.correlation_type;
        return typeof jobType === "string" ? jobType : "";
    }, []);

    const markDraftCompletedImmediately = React.useCallback(
        (caseId: string) => {
            queryClient.setQueryData(
                queryKeys.cases.draft(caseId),
                (oldData: any) => ({
                    subject: oldData?.subject ?? null,
                    body: oldData?.body ?? null,
                    status: oldData?.status ?? "draft",
                    is_generating: false,
                })
            );
        },
        [queryClient]
    );

    const hydrateDraftCache = React.useCallback(
        async (caseId: string) => {
            const freshDraft = await fetchDraftStatus(caseId);
            queryClient.setQueryData(queryKeys.cases.draft(caseId), {
                subject: freshDraft.subject ?? null,
                body: freshDraft.body ?? null,
                status: freshDraft.status,
                is_generating: false,
            });
        },
        [queryClient]
    );

    /**
     * Surgical update helper for list caches (flat arrays or paged items).
     * Uses setQueriesData to find and update the specific case across all matching queries.
     */
    const updateSurgicalCache = React.useCallback(
        (queryKey: readonly unknown[], caseId: string, updater: (item: any) => any) => {
            queryClient.setQueriesData({ queryKey }, (oldData: any) => {
                if (!oldData) return oldData;

                // 1. Handle Paged Response { items: [...] }
                if (oldData.items && Array.isArray(oldData.items)) {
                    return {
                        ...oldData,
                        items: oldData.items.map((item: any) =>
                            item.case_id === caseId ? updater(item) : item
                        ),
                    };
                }

                // 2. Handle Flat Array [...]
                if (Array.isArray(oldData)) {
                    return oldData.map((item: any) =>
                        item.case_id === caseId ? updater(item) : item
                    );
                }

                return oldData;
            });
        },
        [queryClient]
    );

    const handleMessage = React.useCallback(
        async (message: WebSocketMessage) => {
            const { type, payload } = message;
            console.log("[WS] Received message:", type, payload);

            switch (type) {
                case "JOB:STARTED":
                    console.log("[WS] Job started", payload);
                    const startedCaseId = getCaseIdFromJobPayload(payload);
                    const startedJobType = getJobType(payload);
                    if (startedCaseId && startedJobType === "email_draft") {
                        const updater = (item: any) => ({
                            ...item,
                            is_generating: true,
                            draft_status: "generating",
                        });

                        updateSurgicalCache(queryKeys.cases.all, startedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, startedCaseId, updater);
                    }

                    if (startedJobType === "email_draft") {
                        toast.info("Generating email draft...");
                    } else if (startedJobType === "email_send") {
                        toast.info("Sending intervention email...");
                    }
                    break;

                case "JOB:COMPLETED":
                    console.log("[WS] Job completed, surgical cache update...", payload);
                    const completedCaseId = getCaseIdFromJobPayload(payload);
                    const completedJobType = getJobType(payload);
                    if (completedCaseId && completedJobType === "email_draft") {
                        // Surgical update to all lists (Tasks, Open Cases, Alerts, etc.)
                        const updater = (item: any) => ({
                            ...item,
                            is_generating: false,
                            draft_status: "completed",
                        });

                        updateSurgicalCache(queryKeys.cases.all, completedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, completedCaseId, updater);

                        // Phase 1: stop composing state immediately.
                        markDraftCompletedImmediately(completedCaseId);
                    }

                    if (completedJobType === "email_draft") {
                        toast.success("Draft generation completed!");
                        if (completedCaseId) {
                            // Phase 2: hydrate subject/body right after completion.
                            hydrateDraftCache(completedCaseId).catch((error) => {
                                console.error("[WS] Failed to hydrate completed draft:", error);
                            });
                        }
                    } else if (completedJobType === "email_send") {
                        toast.success("Intervention email sent successfully!");
                    }
                    break;

                case "JOB:FAILED":
                    console.error("[WS] Job failed", payload);
                    const failedCaseId = getCaseIdFromJobPayload(payload);
                    const failedJobType = getJobType(payload);
                    if (failedCaseId && failedJobType === "email_draft") {
                        // Surgical update to all lists
                        const updater = (item: any) => ({
                            ...item,
                            is_generating: false,
                            draft_status: "failed",
                        });

                        updateSurgicalCache(queryKeys.cases.all, failedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, failedCaseId, updater);

                        // Invalidate targeted draft query
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.draft(failedCaseId),
                        });
                    }

                    const jobName = failedJobType === "email_draft" ? "Draft generation" : "Email dispatch";
                    toast.error(`${jobName} failed`, {
                        description: ((payload ?? {}) as Record<string, any>).error || "Unknown error occurred",
                    });
                    break;

                case "CASE:STATUS_UPDATED":
                    console.log("[WS] Case status updated, surgical cache update...", payload);
                    if (payload.case_id) {
                        // Surgical update to all lists
                        const updater = (item: any) => ({
                            ...item,
                            intervention_status: payload.new_status,
                            // Fat event: patch appointment details if they are in the payload
                            ...(payload.appointment
                                ? { appointment: payload.appointment }
                                : {}),
                        });

                        updateSurgicalCache(
                            queryKeys.cases.all,
                            payload.case_id,
                            updater
                        );
                        updateSurgicalCache(
                            queryKeys.alerts.all,
                            payload.case_id,
                            updater
                        );

                        // Invalidate specific case details if any component is listening
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.detail(payload.case_id),
                        });
                    }
                    break;

                // Add more cases here (e.g., NEW_ALERT)
                default:
                    console.log("[WS] Unhandled message type:", type);
            }
        },
        [
            getCaseIdFromJobPayload,
            getJobType,
            hydrateDraftCache,
            markDraftCompletedImmediately,
            queryClient,
            updateSurgicalCache,
        ]
    );

    const { status } = useWebSocket({ onMessage: handleMessage });

    return (
        <WebSocketContext.Provider value={{ status }}>
            {children}
        </WebSocketContext.Provider>
    );
}
