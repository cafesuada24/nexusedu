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

    const handleMessage = React.useCallback(
        (message: WebSocketMessage) => {
            const { type, payload } = message;
            console.log("[WS] Received message:", type, payload);

            switch (type) {
                case "JOB:COMPLETED":
                    console.log("[WS] Job completed, surgical cache update...", payload);
                    if (payload.case_id) {
                        // 1. Invalidate broader list queries to ensure the UI updates everywhere
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.all,
                        });
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.alerts.all,
                        });

                        // 2. Invalidate targeted draft query
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.draft(payload.case_id),
                        });

                        // 3. Surgical update to alerts list cache
                        queryClient.setQueryData(
                            queryKeys.alerts.list(),
                            (oldData: any[] | undefined) => {
                                if (!oldData) return oldData;
                                return oldData.map((item) =>
                                    item.case_id === payload.case_id
                                        ? { ...item, is_generating: false, draft_status: "completed" }
                                        : item
                                );
                            }
                        );
                    }
                    toast.success("Draft generation completed!");
                    break;

                case "JOB:FAILED":
                    console.error("[WS] Job failed", payload);
                    if (payload.case_id) {
                        // 1. Invalidate broader list queries
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.all,
                        });
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.alerts.all,
                        });

                        // 2. Invalidate targeted draft query
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.draft(payload.case_id),
                        });

                        // 3. Surgical update to alerts list cache
                        queryClient.setQueryData(
                            queryKeys.alerts.list(),
                            (oldData: any[] | undefined) => {
                                if (!oldData) return oldData;
                                return oldData.map((item) =>
                                    item.case_id === payload.case_id
                                        ? { ...item, is_generating: false, draft_status: "failed" }
                                        : item
                                );
                            }
                        );
                    }
                    toast.error("Draft generation failed", {
                        description: payload.error || "Unknown error occurred",
                    });
                    break;

                case "CASE:STATUS_UPDATED":
                    console.log("[WS] Case status updated, surgical cache update...", payload);
                    if (payload.case_id) {
                        // 1. Invalidate broader list queries to ensure the UI updates everywhere
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.all,
                        });
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.alerts.all,
                        });

                        // 2. Invalidate specific case details
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.cases.detail(payload.case_id),
                        });

                        // 3. Surgical update to alerts list cache for immediate feedback
                        queryClient.setQueryData(
                            queryKeys.alerts.list(),
                            (oldData: any[] | undefined) => {
                                if (!oldData) return oldData;
                                return oldData.map((item) =>
                                    item.case_id === payload.case_id
                                        ? { ...item, intervention_status: payload.new_status }
                                        : item
                                );
                            }
                        );
                    }
                    break;

                // Add more cases here (e.g., NEW_ALERT)
                default:
                    console.log("[WS] Unhandled message type:", type);
            }
        },
        [queryClient]
    );

    const { status } = useWebSocket({ onMessage: handleMessage });

    return (
        <WebSocketContext.Provider value={{ status }}>
            {children}
        </WebSocketContext.Provider>
    );
}
