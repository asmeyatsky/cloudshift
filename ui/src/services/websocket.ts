import type { WSMessage } from "../types";
import { useAuthStore } from "../store/authStore";

export type WSListener = (message: WSMessage) => void;

/**
 * Lightweight WebSocket client for streaming progress updates from the
 * CloudShift backend.  Supports auto-reconnection with exponential backoff.
 * When auth is searce_id and no IAP, the browser cannot set headers on WS;
 * the API key is passed via query param (read at connect time).
 */
export class CloudShiftWebSocket {
  private ws: WebSocket | null = null;
  private listeners = new Set<WSListener>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  private shouldReconnect = true;
  private readonly path: string;

  constructor(path = "/ws/progress") {
    this.path = path;
  }

  private buildUrl(): string {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    let url = `${proto}//${window.location.host}${this.path}`;
    const raw =
      useAuthStore.getState().apiKey ??
      (typeof window !== "undefined" ? (window as unknown as { __CLOUDSHIFT_API_KEY__?: string }).__CLOUDSHIFT_API_KEY__ : null);
    const apiKey = typeof raw === "string" ? raw.trim() : "";
    if (apiKey) {
      url += (url.includes("?") ? "&" : "?") + "api_key=" + encodeURIComponent(apiKey);
    }
    return url;
  }

  /* -------------------------------------------------------------- */
  /*  Public API                                                     */
  /* -------------------------------------------------------------- */

  connect(): void {
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.createConnection();
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  subscribe(listener: WSListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  send(message: WSMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /* -------------------------------------------------------------- */
  /*  Internals                                                      */
  /* -------------------------------------------------------------- */

  private createConnection(): void {
    if (this.ws) {
      this.ws.close();
    }

    this.ws = new WebSocket(this.buildUrl());

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data as string) as WSMessage;
        this.listeners.forEach((fn) => fn(message));
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectAttempts += 1;
    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      return;
    }
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay,
      );
      this.createConnection();
    }, this.reconnectDelay);
  }
}

/** Singleton instance used across the app. */
export const wsClient = new CloudShiftWebSocket();
