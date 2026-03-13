import { useCallback, useRef } from "react";
import { refactorApi } from "../services/api";
import { useProjectStore, useOperationStore } from "../store";
import type { FileDiff } from "../types";

/**
 * Single hook replacing useScan + usePlan + useApply.
 * Streams NDJSON from POST /api/refactor/project and populates the same
 * `diffs` array in useOperationStore that DiffPage already reads.
 */
export function useRefactor() {
  const abortRef = useRef<AbortController | null>(null);

  const startRefactor = useCallback(async () => {
    const activeProject = useProjectStore.getState().activeProject;
    if (!activeProject) throw new Error("No project selected");

    const store = useOperationStore.getState();
    if (store.running) throw new Error("Already running");

    store.setRunning(true);
    store.setError(null);
    store.setDiffs([]);
    store.setRefactorProgress(null);
    store.setRefactorSummary(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await refactorApi.startProject(
        {
          project_id: activeProject.id,
          source_provider: activeProject.sourceProvider.toUpperCase(),
          target_provider: activeProject.targetProvider.toUpperCase(),
          root_path: activeProject.path,
        },
        controller.signal,
      );

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        let detail = response.statusText;
        try {
          const parsed = JSON.parse(text);
          detail = parsed.detail ?? parsed.message ?? detail;
        } catch { /* use statusText */ }
        throw new Error(detail);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep incomplete last line in buffer
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          let event: Record<string, unknown>;
          try {
            event = JSON.parse(trimmed);
          } catch {
            continue;
          }

          const eventType = event.type as string;

          if (eventType === "progress") {
            useOperationStore.getState().setRefactorProgress({
              current: (event.index as number) + 1,
              total: event.total as number,
              currentFile: event.file as string,
            });
          } else if (eventType === "file_result" && event.changed) {
            const diff: FileDiff = {
              filePath: event.file as string,
              original: (event.original as string) ?? "",
              modified: (event.modified as string) ?? "",
              hunks: [],
              stats: { additions: 0, deletions: 0 },
            };
            const current = useOperationStore.getState().diffs;
            useOperationStore.getState().setDiffs([...current, diff]);
          } else if (eventType === "complete") {
            useOperationStore.getState().setRefactorSummary({
              total: event.total as number,
              changed: event.changed as number,
              patternCount: event.pattern_count as number,
              llmCount: event.llm_count as number,
              skipped: event.skipped as number,
              llmConfigured: event.llm_configured as boolean,
            });
          } else if (eventType === "error") {
            throw new Error(event.message as string);
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // User cancelled — not an error
      } else {
        const msg = err instanceof Error ? err.message : "Refactor failed";
        useOperationStore.getState().setError(msg);
        throw err;
      }
    } finally {
      useOperationStore.getState().setRunning(false);
      useOperationStore.getState().setRefactorProgress(null);
      abortRef.current = null;
    }
  }, []);

  const cancelRefactor = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { startRefactor, cancelRefactor };
}
