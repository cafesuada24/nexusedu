/**
 * Socket.io Client Utility
 * 
 * In production:
 * import { io } from "socket.io-client";
 * export const socket = io(process.env.NEXT_PUBLIC_SOCKET_URL || "http://localhost:8000");
 * 
 * Mock implementation for demonstration:
 */

type Callback = (data: any) => void;

class MockSocket {
  private listeners: Record<string, Callback[]> = {};

  on(event: string, callback: Callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  }

  off(event: string, callback: Callback) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter((cb) => cb !== callback);
  }

  emit(event: string, data: any) {
    // eslint-disable-next-line no-console
    console.log(`[Socket] Emitting ${event}:`, data);
    
    // Simulate network latency and broadcast
    setTimeout(() => {
      if (this.listeners[event]) {
        this.listeners[event].forEach((cb) => cb(data));
      }
    }, 500);
  }
}

export const socket = new MockSocket() as any; // Cast as any for demo simplicity
