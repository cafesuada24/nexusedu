"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/hooks/use-auth";

export interface WebSocketMessage<T = unknown> {
  type: string;
  payload: T;
  user_id?: string | null;
}

type ConnectionStatus = "connecting" | "open" | "closed";

const RECONNECT_DELAY = 5_000;
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
      // Explicit WS URL has highest priority
      if (process.env.NEXT_PUBLIC_WS_URL) {
        return process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "");
      }

      const apiBaseUrl = (
        process.env.NEXT_PUBLIC_API_BASE_URL ?? ""
      ).replace(/\/+$/, "");

      // Absolute API URL
      if (apiBaseUrl.startsWith("http")) {
        const wsBaseUrl = apiBaseUrl.replace(/^http/, "ws");

        return `${wsBaseUrl}/ws`;
      }

      // Fallback
      const isDev = process.env.NODE_ENV === "development";

      const protocol =
        window.location.protocol === "https:"
          ? "wss:"
          : "ws:";

      const host = isDev
        ? "localhost:8000"
        : window.location.host;

      return `${protocol}//${host}/api/v1/ws`;
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

      console.debug("[WS] Scheduling reconnect...");
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, RECONNECT_DELAY);
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
