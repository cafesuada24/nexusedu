"use client";

import React, { createContext, useContext, useEffect } from "react";
import { useWebSocket, WebSocketMessage } from "@/hooks/use-websocket";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
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
        (message: WebSocketMessage) => {
            const { type, payload } = message;
            console.log("[WS] Received message:", type, payload);

            switch (type) {
                case "JOB:STARTED":
                    console.log("[WS] Job started", payload);
                    const startedCaseId = payload.metadata?.case_id;
                    if (startedCaseId) {
                        const updater = (item: any) => ({
                            ...item,
                            is_generating: true,
                            draft_status: "generating",
                        });

                        updateSurgicalCache(queryKeys.cases.all, startedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, startedCaseId, updater);
                    }

                    if (payload.job_type === "email_draft") {
                        toast.info("Generating email draft...");
                    } else if (payload.job_type === "email_send") {
                        toast.info("Sending intervention email...");
                    }
                    break;

                case "JOB:COMPLETED":
                    console.log("[WS] Job completed, surgical cache update...", payload);
                    const completedCaseId = payload.metadata?.case_id;
                    if (completedCaseId) {
                        // Surgical update to all lists (Tasks, Open Cases, Alerts, etc.)
                        const updater = (item: any) => ({
                            ...item,
                            is_generating: false,
                            draft_status: "completed",
                        });

                        updateSurgicalCache(queryKeys.cases.all, completedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, completedCaseId, updater);

                        // Invalidate targeted draft query since it's a single item fetch
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.draft(completedCaseId),
                        });
                    }

                    if (payload.job_type === "email_draft") {
                        toast.success("Draft generation completed!");
                    } else if (payload.job_type === "email_send") {
                        toast.success("Intervention email sent successfully!");
                    }
                    break;

                case "JOB:FAILED":
                    console.error("[WS] Job failed", payload);
                    const failedCaseId = payload.metadata?.case_id;
                    if (failedCaseId) {
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

                    const jobName = payload.job_type === "email_draft" ? "Draft generation" : "Email dispatch";
                    toast.error(`${jobName} failed`, {
                        description: payload.error || "Unknown error occurred",
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
        [queryClient, updateSurgicalCache]
    );

    const { status } = useWebSocket({ onMessage: handleMessage });

    return (
        <WebSocketContext.Provider value={{ status }}>
            {children}
        </WebSocketContext.Provider>
    );
}
