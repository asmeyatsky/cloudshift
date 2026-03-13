/**
 * @vitest-environment jsdom
 *
 * Tests for Fix 1 (plan polling retry) and Fix 2 (stale closure).
 *
 * These tests exercise the actual usePlan hook's createPlan function
 * with mocked API responses to verify that:
 *   - "not found" 404s during polling trigger retry (not abort)
 *   - "in progress" 404s during polling trigger retry
 *   - mixed sequences (404 → 404 → success) resolve correctly
 *   - fresh state is read from Zustand (not stale closure)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePlan } from "./usePlan";
import { useProjectStore, useOperationStore } from "../store";
import * as api from "../services/api";

// Advance fake timers past the poll interval
async function advanceOnePoll() {
  await vi.advanceTimersByTimeAsync(2100);
}

describe("usePlan polling (Fix 1 & 2)", () => {
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
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("retries on 'Plan not found or still in progress' and resolves on success", async () => {
    // planApi.create succeeds immediately
    vi.spyOn(api.planApi, "create").mockResolvedValue({
      success: true,
      data: { job_id: "j1", status: "accepted" },
    });

    // First two polls: 404 "not found" — must retry, not abort
    // Third poll: success
    const getSpy = vi.spyOn(api.planApi, "get")
      .mockResolvedValueOnce({ success: false, error: "Plan not found or still in progress" })
      .mockResolvedValueOnce({ success: false, error: "Plan not found or still in progress" })
      .mockResolvedValueOnce({
        success: true,
        data: { plan_id: "plan-1", project_id: "proj-1", steps: [], steps_by_pattern: [] } as any,
      });

    vi.spyOn(api.planApi, "getDiffs").mockResolvedValue({ success: true, data: [] });

    const { result } = renderHook(() => usePlan());

    let promise: Promise<void>;
    act(() => {
      promise = result.current.createPlan();
    });

    // First poll fires immediately — gets "not found", schedules retry
    await act(() => advanceOnePoll());
    expect(getSpy).toHaveBeenCalledTimes(2);

    // Second poll — still "not found", schedules retry
    await act(() => advanceOnePoll());
    expect(getSpy).toHaveBeenCalledTimes(3);

    // Third poll — success
    await act(async () => {
      await promise;
    });

    expect(useOperationStore.getState().planResult).not.toBeNull();
    expect(useOperationStore.getState().planResult!.id).toBe("plan-1");
    expect(useOperationStore.getState().error).toBeNull();
    expect(useOperationStore.getState().running).toBe(false);
  });

  it("retries on 'in progress' message", async () => {
    vi.spyOn(api.planApi, "create").mockResolvedValue({
      success: true,
      data: { job_id: "j1", status: "accepted" },
    });

    vi.spyOn(api.planApi, "get")
      .mockResolvedValueOnce({ success: false, error: "Plan still in progress" })
      .mockResolvedValueOnce({
        success: true,
        data: { plan_id: "plan-2", project_id: "proj-1", steps: [], steps_by_pattern: [] } as any,
      });

    vi.spyOn(api.planApi, "getDiffs").mockResolvedValue({ success: true, data: [] });

    const { result } = renderHook(() => usePlan());

    let promise: Promise<void>;
    act(() => {
      promise = result.current.createPlan();
    });

    await act(() => advanceOnePoll());
    await act(async () => {
      await promise;
    });

    expect(useOperationStore.getState().planResult!.id).toBe("plan-2");
  });

  it("aborts on non-retryable error", async () => {
    vi.spyOn(api.planApi, "create").mockResolvedValue({
      success: true,
      data: { job_id: "j1", status: "accepted" },
    });

    vi.spyOn(api.planApi, "get")
      .mockResolvedValueOnce({ success: false, error: "Internal server error" });

    const { result } = renderHook(() => usePlan());

    let err: Error | undefined;
    act(() => {
      result.current.createPlan().catch((e: Error) => { err = e; });
    });

    // Let the first poll fire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(err).toBeDefined();
    expect(err!.message).toContain("Internal server error");
    expect(useOperationStore.getState().running).toBe(false);
  });

  it("uses fresh project from getState (Fix 2: stale closure)", async () => {
    const createSpy = vi.spyOn(api.planApi, "create").mockResolvedValue({
      success: true,
      data: { job_id: "j1", status: "accepted" },
    });

    vi.spyOn(api.planApi, "get").mockResolvedValue({
      success: true,
      data: { plan_id: "plan-3", project_id: "proj-2", steps: [], steps_by_pattern: [] } as any,
    });

    vi.spyOn(api.planApi, "getDiffs").mockResolvedValue({ success: true, data: [] });

    // Render with proj-1
    const { result } = renderHook(() => usePlan());

    // Simulate pipeline: update store to proj-2 AFTER render (stale closure scenario)
    useProjectStore.getState().setActiveProject({
      id: "proj-2",
      name: "test2",
      path: "/tmp/test2",
      sourceProvider: "aws",
      targetProvider: "gcp",
      importedAt: new Date().toISOString(),
    });

    await act(async () => {
      await result.current.createPlan();
    });

    // Should use proj-2 (fresh from getState), not proj-1 (stale closure)
    expect(createSpy).toHaveBeenCalledWith("proj-2", "proj-2");
  });

  it("does not start if running flag is true in store (Fix 2: stale running)", async () => {
    // Set running in store after render
    useOperationStore.getState().setRunning(true);

    const { result } = renderHook(() => usePlan());

    let err: Error | undefined;
    try {
      await result.current.createPlan();
    } catch (e) {
      err = e as Error;
    }

    expect(err).toBeDefined();
    expect(err!.message).toContain("Already running");
  });
});
