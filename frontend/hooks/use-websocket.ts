"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "@/hooks/use-auth";

export interface WebSocketMessage {
  type: string;
  payload: any;
  user_id?: string | null;
}

export function useWebSocket() {
  const { token, isAuthenticated } = useAuth();
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("closed");
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!token || !isAuthenticated) return;

    // Clear existing socket
    if (socketRef.current) {
      socketRef.current.close();
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";

    // Construct WS URL. Handle relative URLs if necessary.
    let wsUrl: string;
    if (baseUrl.startsWith("http")) {
      wsUrl = baseUrl.replace(/^http/, "ws") + "/v1/ws?token=" + token;
    } else {
      wsUrl = `${wsProtocol}//${window.location.host}${baseUrl}/api/v1/ws?token=${token}`;
    }

    console.log("[useWebSocket] Connecting to", wsUrl.split("?")[0]);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => {
      console.log("[useWebSocket] Connection established");
      setStatus("open");
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        console.log("[useWebSocket] Received:", data.type, data.payload);
        setLastMessage(data);
      } catch (err) {
        console.error("[useWebSocket] Failed to parse message:", err);
      }
    };

    ws.onclose = (event) => {
      console.log("[useWebSocket] Connection closed", event.code);
      setStatus("closed");

      // Reconnect if not closed normally
      if (event.code !== 1000 && event.code !== 4003) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 5000);
      }
    };

    ws.onerror = (err) => {
      console.error("[useWebSocket] Error:", err);
      ws.close();
    };
  }, [token, isAuthenticated]);

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        socketRef.current.close(1000);
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { lastMessage, status };
}
