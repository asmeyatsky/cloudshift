import { useEffect, useRef } from "react";
import { wsClient } from "../services/websocket";
import type { WSMessage, ProgressPayload } from "../types";
import { useOperationStore } from "../store";

/**
 * Connects the global WebSocket client on mount and routes incoming
 * messages to the appropriate Zustand stores.
 */
export function useWebSocket() {
  const setProgress = useOperationStore((s) => s.setProgress);
  const setRunning = useOperationStore((s) => s.setRunning);
  const setError = useOperationStore((s) => s.setError);
  const connectedRef = useRef(false);

  useEffect(() => {
    if (connectedRef.current) return;
    connectedRef.current = true;

    wsClient.connect();

    const unsub = wsClient.subscribe((msg: WSMessage) => {
      switch (msg.type) {
        case "progress":
          setProgress(msg.payload as ProgressPayload);
          break;
        case "scan_complete":
        case "plan_complete":
        case "apply_complete":
        case "validation_complete":
          setRunning(false);
          setProgress(null);
          break;
        case "error":
          setError((msg.payload as { message: string }).message);
          setRunning(false);
          setProgress(null);
          break;
      }
    });

    return () => {
      unsub();
      wsClient.disconnect();
      connectedRef.current = false;
    };
  }, [setProgress, setRunning, setError]);

  return { connected: wsClient.connected };
}
