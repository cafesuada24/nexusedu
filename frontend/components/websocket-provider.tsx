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
    const { lastMessage, status } = useWebSocket();
    const queryClient = useQueryClient();

    useEffect(() => {
        if (!lastMessage) return;

        const { type, payload } = lastMessage;

        switch (type) {
            case "JOB_COMPLETED":
                console.log("[WS] Job completed, invalidating queries...", payload);
                if (payload.case_id) {
                    queryClient.invalidateQueries({
                        queryKey: queryKeys.cases.draft(payload.case_id),
                    });
                    queryClient.invalidateQueries({
                        queryKey: queryKeys.alerts.list(),
                    });
                }
                toast.success("Draft generation completed!");
                break;

            case "JOB_FAILED":
                console.error("[WS] Job failed", payload);
                if (payload.case_id) {
                    queryClient.invalidateQueries({
                        queryKey: queryKeys.cases.draft(payload.case_id),
                    });
                }
                toast.error("Draft generation failed", {
                    description: payload.error || "Unknown error occurred",
                });
                break;
            
            // Add more cases here (e.g., NEW_ALERT, STATUS_CHANGED)
            default:
                console.log("[WS] Unhandled message type:", type);
        }
    }, [lastMessage, queryClient]);

    return (
        <WebSocketContext.Provider value={{ status }}>
            {children}
        </WebSocketContext.Provider>
    );
}
