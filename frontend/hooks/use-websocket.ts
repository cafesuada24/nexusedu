"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { getWsUrl } from "@/lib/api";

export interface WebSocketMessage<T = unknown> {
  type: string;
  payload: T;
  user_id?: string | null;
}

type ConnectionStatus = "connecting" | "open" | "closed";

const RECONNECT_DELAY = 1_000; // Base delay for exponential backoff
const MAX_RECONNECT_DELAY = 30_000; // Maximum delay between reconnections
const NORMAL_CLOSE_CODE = 1000;
const UNAUTHORIZED_CLOSE_CODE = 4003;

export interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { authReady, isAuthenticated } = useAuth();
  const { onMessage } = options;

  const [lastMessage, setLastMessage] =
    useState<WebSocketMessage | null>(null);

  const [status, setStatus] =
    useState<ConnectionStatus>("closed");

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  const manuallyClosedRef = useRef(false);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const clearReconnectTimeout = useCallback(() => {
    if (!reconnectTimeoutRef.current) {
      return;
    }

    clearTimeout(reconnectTimeoutRef.current);
    reconnectTimeoutRef.current = null;
  }, []);

  const disconnect = useCallback(
    (code: number = NORMAL_CLOSE_CODE) => {
      manuallyClosedRef.current = true;
      reconnectAttemptRef.current = 0;

      clearReconnectTimeout();

      const socket = socketRef.current;

      if (
        socket &&
        (
          socket.readyState === WebSocket.OPEN ||
          socket.readyState === WebSocket.CONNECTING
        )
      ) {
        socket.close(code);
      }

      socketRef.current = null;
      setStatus("closed");
    },
    [clearReconnectTimeout],
  );

  const buildWebSocketUrl = useCallback(
    () => {
      if (typeof window === "undefined") return "";
      
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("nexusedu_ws_token="))
        ?.split("=")[1];

      let url = getWsUrl(token);

      // Surgical fix: Ensure /api/v1 prefix is present if missing on localhost:8000
      if (url.includes("localhost:8000") && !url.includes("/api/v1/")) {
        url = url.replace("/ws", "/api/v1/ws");
      }

      return url;
    },
    [],
  );

  const connect = useCallback(() => {
    console.debug("[WS] Connect attempt. authReady:", authReady, "isAuthenticated:", isAuthenticated);
    if (!authReady || !isAuthenticated) {
      console.debug("[WS] Not ready or not authenticated, ensuring disconnected.");
      disconnect();

      return;
    }

    const currentSocket = socketRef.current;

    // Prevent duplicate connections
    if (
      currentSocket &&
      (
        currentSocket.readyState === WebSocket.OPEN ||
        currentSocket.readyState === WebSocket.CONNECTING
      )
    ) {
      console.debug("[WS] Already connected or connecting, skipping.");
      return;
    }

    manuallyClosedRef.current = false;

    clearReconnectTimeout();

    const wsUrl = buildWebSocketUrl();

    setStatus("connecting");
    console.info("[WS] Connecting to:", wsUrl);

    const socket = new WebSocket(wsUrl);

    socketRef.current = socket;

    socket.onopen = () => {
      // Ensure we only update status if this is still the current socket
      if (socketRef.current === socket) {
        setStatus("open");
        reconnectAttemptRef.current = 0; // Reset attempts on successful connection
        console.info("[WS] Connected successfully");
      }
    };

    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        console.debug("[WS] Raw message received:", event.data);
        const parsedMessage: WebSocketMessage = JSON.parse(
          event.data,
        );

        console.info("[WS] Processed message:", parsedMessage.type, parsedMessage.payload);
        setLastMessage(parsedMessage);
        onMessageRef.current?.(parsedMessage);
      } catch (error) {
        console.error(
          "[WS] Failed to parse message:",
          error,
        );
      }
    };

    socket.onerror = (error) => {
      console.error("[WS] Error:", error);
    };

    socket.onclose = (event: CloseEvent) => {
      console.info(`[WS] Closed (${event.code}) ${event.reason}`);
      
      // Only update state if this was our current socket
      if (socketRef.current === socket) {
        socketRef.current = null;
        setStatus("closed");
      }

      // Do not reconnect if:
      // - manually disconnected
      // - unauthorized
      // - normal closure
      if (
        manuallyClosedRef.current ||
        event.code === NORMAL_CLOSE_CODE ||
        event.code === UNAUTHORIZED_CLOSE_CODE
      ) {
        return;
      }

      const delay = Math.min(
        RECONNECT_DELAY * Math.pow(2, reconnectAttemptRef.current),
        MAX_RECONNECT_DELAY
      );

      console.debug(`[WS] Scheduling reconnect in ${delay}ms (attempt ${reconnectAttemptRef.current + 1})...`);
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectAttemptRef.current += 1;
        connect();
      }, delay);
    };
  }, [
    isAuthenticated,
    authReady,
    disconnect,
    clearReconnectTimeout,
    buildWebSocketUrl,
  ]);

  const sendMessage = useCallback(
    (message: WebSocketMessage) => {
      const socket = socketRef.current;

      if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.warn(
          "[WebSocket] Cannot send message: socket is not open",
        );

        return false;
      }

      socket.send(JSON.stringify(message));

      return true;
    },
    [],
  );

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    lastMessage,
    status,
    sendMessage,
    reconnect: connect,
    disconnect,
    socket: socketRef.current,
  };
}
