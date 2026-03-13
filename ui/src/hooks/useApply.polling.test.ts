/**
 * @vitest-environment jsdom
 *
 * Tests for Fix 1: apply polling retry on 404.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useApply } from "./useApply";
import { useProjectStore, useOperationStore } from "../store";
import * as api from "../services/api";

async function advanceOnePoll() {
  await vi.advanceTimersByTimeAsync(2100);
}

describe("useApply polling (Fix 1)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useOperationStore.getState().reset();
    useProjectStore.getState().setActiveProject({
      id: "proj-1",
      name: "test",
      path: "/tmp/test",
      sourceProvider: "aws",
      targetProvider: "gcp",
      importedAt: new Date().toISOString(),
    });
    useOperationStore.getState().setPlanResult({
      id: "plan-1",
      manifestId: "proj-1",
      transformations: [],
      stepsByPattern: [],
      diffs: [],
      estimatedChanges: 0,
      riskLevel: "info",
      timestamp: "",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("retries on 'Apply not found or still in progress' and resolves on success", async () => {
    vi.spyOn(api.applyApi, "start").mockResolvedValue({
      success: true,
      data: { job_id: "aj1", status: "accepted" },
    });

    const statusSpy = vi.spyOn(api.applyApi, "status")
      .mockResolvedValueOnce({ success: false, error: "Apply not found or still in progress" })
      .mockResolvedValueOnce({ success: false, error: "Apply not found or still in progress" })
      .mockResolvedValueOnce({
        success: true,
        data: {
          plan_id: "plan-1",
          applied_steps: ["s1"],
          files_modified: 1,
          modified_file_details: [
            { path: "main.py", original_content: "import boto3", modified_content: "from google.cloud import storage" },
          ],
        } as any,
      });

    const { result } = renderHook(() => useApply());

    let promise: Promise<void>;
    act(() => {
      promise = result.current.startApply();
    });

    // First poll — "not found" → retry
    await act(() => advanceOnePoll());
    expect(statusSpy).toHaveBeenCalledTimes(2);

    // Second poll — "not found" → retry
    await act(() => advanceOnePoll());
    expect(statusSpy).toHaveBeenCalledTimes(3);

    // Third poll — success
    await act(async () => {
      await promise;
    });

    expect(useOperationStore.getState().applyResult).not.toBeNull();
    expect(useOperationStore.getState().applyResult!.planId).toBe("plan-1");
    expect(useOperationStore.getState().running).toBe(false);
  });

  it("aborts on non-retryable error", async () => {
    vi.spyOn(api.applyApi, "start").mockResolvedValue({
      success: true,
      data: { job_id: "aj1", status: "accepted" },
    });

    vi.spyOn(api.applyApi, "status")
      .mockResolvedValueOnce({ success: false, error: "Internal server error" });

    const { result } = renderHook(() => useApply());

    let err: Error | undefined;
    act(() => {
      result.current.startApply().catch((e: Error) => { err = e; });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(err).toBeDefined();
    expect(err!.message).toContain("Internal server error");
    expect(useOperationStore.getState().running).toBe(false);
  });
});
