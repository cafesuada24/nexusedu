"use client";

import { useEffect } from "react";
import { socket } from "@/lib/socket";

/**
 * Modular hook to listen for specific socket events.
 * 
 * @param event - The name of the socket event (e.g., 'new_appointment')
 * @param callback - Function to execute when the event is received
 */
export function useSocketEvent<T>(event: string, callback: (data: T) => void) {
  useEffect(() => {
    socket.on(event, callback);

    return () => {
      socket.off(event, callback);
    };
  }, [event, callback]);
}

/**
 * Hook to get the raw socket instance if needed for emitting events.
 */
export function useSocket() {
  return socket;
}
