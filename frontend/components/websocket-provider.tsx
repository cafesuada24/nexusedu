"use client";

import React, { createContext, useContext, useEffect } from "react";
import { useWebSocket, WebSocketMessage } from "@/hooks/use-websocket";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { fetchDraftStatus } from "@/lib/api";
import { toast } from "sonner";

interface WebSocketContextType {
    status: "connecting" | "open" | "closed";
    latestDraftCompletion: {
        caseId: string;
        subject: string | null;
        body: string | null;
        sequence: number;
    } | null;
    lastMessage: WebSocketMessage | null;
}

const WebSocketContext = createContext<WebSocketContextType>({
    status: "closed",
    latestDraftCompletion: null,
    lastMessage: null,
});

export const useWebSocketContext = () => useContext(WebSocketContext);

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
    const queryClient = useQueryClient();
    const [latestDraftCompletion, setLatestDraftCompletion] = React.useState<{
        caseId: string;
        subject: string | null;
        body: string | null;
        sequence: number;
    } | null>(null);
    const [lastMessage, setLastMessage] = React.useState<WebSocketMessage | null>(null);
    const getCaseIdFromJobPayload = React.useCallback((rawPayload: unknown) => {
        const payload = (rawPayload ?? {}) as Record<string, any>;
        const rootCaseId = payload.case_id ?? payload.caseId;
        if (typeof rootCaseId === "string" && rootCaseId) {
            return rootCaseId;
        }
        const metadataCaseId = payload.metadata?.case_id;
        if (typeof metadataCaseId === "string" && metadataCaseId) {
            return metadataCaseId;
        }
        const metadataCaseIdCamel = payload.metadata?.caseId;
        if (typeof metadataCaseIdCamel === "string" && metadataCaseIdCamel) {
            return metadataCaseIdCamel;
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
                            (item.case_id === caseId || item.caseId === caseId) ? updater(item) : item
                        ),
                    };
                }

                // 2. Handle Flat Array [...]
                if (Array.isArray(oldData)) {
                    return oldData.map((item: any) =>
                        (item.case_id === caseId || item.caseId === caseId) ? updater(item) : item
                    );
                }

                return oldData;
            });
        },
        [queryClient]
    );

    const markDraftCompletedImmediately = React.useCallback(
        (caseId: string, payload?: any) => {
            // Update the targeted draft query
            queryClient.setQueryData(
                queryKeys.cases.draft(caseId),
                (oldData: any) => ({
                    subject: payload?.subject ?? oldData?.subject ?? null,
                    body: payload?.body ?? oldData?.body ?? null,
                    status: "draft",
                    is_generating: false,
                })
            );

            // Surgical update to all lists (Tasks, Open Cases, Alerts, etc.)
            const updater = (item: any) => ({
                ...item,
                is_generating: false,
                isGenerating: false, // For Alert objects
                draft_status: "draft",
                draftStatus: "draft", // For Alert objects
                ...(payload?.subject ? { draft_subject: payload.subject, draftSubject: payload.subject } : {}),
                ...(payload?.body ? { draft_body: payload.body, draftBody: payload.body } : {}),
            });

            updateSurgicalCache(queryKeys.cases.all, caseId, updater);
            updateSurgicalCache(queryKeys.alerts.all, caseId, updater);
            updateSurgicalCache(queryKeys.alerts.list(), caseId, updater);

            setLatestDraftCompletion({
                caseId,
                subject: payload?.subject ?? null,
                body: payload?.body ?? null,
                sequence: Date.now(),
            });
        },
        [queryClient, updateSurgicalCache]
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

            // Surgically update list caches so "Edit Email" sheet sees the content immediately
            const updater = (item: any) => ({
                ...item,
                draft_subject: freshDraft.subject ?? null,
                draftSubject: freshDraft.subject ?? null, // For Alert objects
                draft_body: freshDraft.body ?? null,
                draftBody: freshDraft.body ?? null, // For Alert objects
                draft_status: freshDraft.status,
                draftStatus: freshDraft.status, // For Alert objects
                is_generating: false,
                isGenerating: false, // For Alert objects
            });
            updateSurgicalCache(queryKeys.cases.all, caseId, updater);
            updateSurgicalCache(queryKeys.alerts.all, caseId, updater);
            updateSurgicalCache(queryKeys.alerts.list(), caseId, updater);

            setLatestDraftCompletion({
                caseId,
                subject: freshDraft.subject ?? null,
                body: freshDraft.body ?? null,
                sequence: Date.now(),
            });
        },
        [queryClient, updateSurgicalCache]
    );

    const handleMessage = React.useCallback(
        async (message: WebSocketMessage) => {
            const { type, payload } = message;
            console.log("[WS] Received message:", type, payload);
            setLastMessage(message);

            switch (type) {
                case "JOB:STARTED":
                    console.log("[WS] Job started", payload);
                    const startedCaseId = getCaseIdFromJobPayload(payload);
                    const startedJobType = getJobType(payload);
                    if (startedCaseId && startedJobType === "email_draft") {
                        const updater = (item: any) => ({
                            ...item,
                            is_generating: true,
                            isGenerating: true, // For Alert objects
                            draft_status: "generating",
                            draftStatus: "generating", // For Alert objects
                        });

                        updateSurgicalCache(queryKeys.cases.all, startedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, startedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.list(), startedCaseId, updater);
                    }

                    if (startedJobType === "email_draft") {
                        toast.info("Generating email draft...");
                    } else if (startedJobType === "email_send") {
                        // toast.info("Sending intervention email...");
                    }
                    break;

                case "JOB:COMPLETED":
                    console.log("[WS] Job completed, surgical cache update...", payload);
                    const completedCaseId = getCaseIdFromJobPayload(payload);
                    const completedJobType = getJobType(payload);
                    if (completedCaseId && completedJobType === "email_draft") {
                        // Phase 1: stop composing state immediately and update content if available.
                        markDraftCompletedImmediately(completedCaseId, payload);
                    }

                    if (completedJobType === "email_draft") {
                        toast.success("Draft generation completed!");
                        if (completedCaseId) {
                            // Phase 2: hydrate subject/body right after completion (ensures we have latest even if WS payload was partial).
                            hydrateDraftCache(completedCaseId).catch((error) => {
                                console.error("[WS] Failed to hydrate completed draft:", error);
                            });
                        }
                    } else if (completedJobType === "email_send") {
                        // toast.success("Intervention email sent successfully!");
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
                            isGenerating: false, // For Alert objects
                            draft_status: "failed",
                            draftStatus: "failed", // For Alert objects
                        });

                        updateSurgicalCache(queryKeys.cases.all, failedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.all, failedCaseId, updater);
                        updateSurgicalCache(queryKeys.alerts.list(), failedCaseId, updater);

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

                case "DATA:INGESTED":
                    const ingestPayload = payload as any;
                    console.log("[WS] Data ingested, invalidating caches...", ingestPayload);
                    toast.success("Data ingestion complete", {
                        description: ingestPayload.new_cases_count > 0 
                            ? `Ingestion finished. ${ingestPayload.new_cases_count} new at-risk cases identified.`
                            : "Ingestion finished. No new cases identified.",
                    });

                    // Invalidate caches that might have changed
                    queryClient.invalidateQueries({ queryKey: queryKeys.alerts.all });
                    queryClient.invalidateQueries({ queryKey: queryKeys.cases.all });
                    queryClient.invalidateQueries({ queryKey: queryKeys.metrics.stats });
                    break;

                case "CASE:STATUS_UPDATED":
                    const statusPayload = payload as any;
                    console.log("[WS] Case status updated, surgical cache update...", statusPayload);
                    if (statusPayload.case_id) {
                        // toast.info("Case status updated", {
                        //     description: `Case ${statusPayload.case_id.slice(0, 8)} status changed to ${statusPayload.new_status}.`,
                        // });
                        // Surgical update to all lists
                        const updater = (item: any) => ({
                            ...item,
                            intervention_status: statusPayload.new_status,
                            // Fat event: patch appointment details if they are in the payload
                            ...(statusPayload.appointment
                                ? { appointment: statusPayload.appointment }
                                : {}),
                        });

                        updateSurgicalCache(
                            queryKeys.cases.all,
                            statusPayload.case_id,
                            updater
                        );
                        updateSurgicalCache(
                            queryKeys.alerts.all,
                            statusPayload.case_id,
                            updater
                        );
                        updateSurgicalCache(
                            queryKeys.alerts.list(),
                            statusPayload.case_id,
                            updater
                        );

                        // Invalidate specific case details if any component is listening
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.detail(statusPayload.case_id),
                        });
                    }
                    break;

                case "CASE:OVERVIEW_GENERATED":
                    const overviewPayload = payload as any;
                    console.log("[WS] Case overview generated, surgical cache update...", overviewPayload);
                    if (overviewPayload.case_id) {
                        toast.success("AI Case Overview generated", {
                            description: `Academic summary for case ${overviewPayload.case_id.slice(0, 8)} is ready.`,
                        });
                        const updater = (item: any) => ({
                            ...item,
                            ai_overview: {
                                academic_summary: overviewPayload.academic_summary,
                                action_keys: overviewPayload.action_keys,
                            },
                        });

                        updateSurgicalCache(queryKeys.cases.all, overviewPayload.case_id, updater);
                        updateSurgicalCache(queryKeys.alerts.all, overviewPayload.case_id, updater);
                        updateSurgicalCache(queryKeys.alerts.list(), overviewPayload.case_id, updater);

                        // Invalidate detail cache to ensure consistency
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.detail(overviewPayload.case_id),
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

    React.useEffect(() => {
        console.info(`[WS] Connection status changed: ${status}`);
    }, [status]);

    return (
        <WebSocketContext.Provider value={{ status, latestDraftCompletion, lastMessage }}>
            {children}
        </WebSocketContext.Provider>
    );
}
