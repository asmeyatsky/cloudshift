/**
 * API service tests: verify request shapes for pipeline flow (scan → plan → apply → validate).
 * Ensures UI sends project_id, manifest_id, plan_id consistently with API and docs/pipeline-flows.md.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { scanApi, planApi, applyApi, validationApi } from "./api";

describe("api pipeline flow", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("scan start sends root_path, providers, and optional project_id", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "j1" }),
    });
    await scanApi.start("/path", "AWS", "GCP", "proj-1");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/scan"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("project_id"),
      }),
    );
    const req = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse((req?.body as string) ?? "{}");
    expect(body.root_path).toBe("/path");
    expect(body.source_provider).toBe("AWS");
    expect(body.target_provider).toBe("GCP");
    expect(body.project_id).toBe("proj-1");
  });

  it("scan start without project_id omits project_id", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "j1" }),
    });
    await scanApi.start("/path", "AWS", "GCP");
    const req = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse((req?.body as string) ?? "{}");
    expect(body).not.toHaveProperty("project_id");
  });

  it("plan create sends project_id and manifest_id", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "j2" }),
    });
    await planApi.create("proj-1", "proj-1");
    const req = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse((req?.body as string) ?? "{}");
    expect(body.project_id).toBe("proj-1");
    expect(body.manifest_id).toBe("proj-1");
  });

  it("apply start sends plan_id", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "j3" }),
    });
    await applyApi.start("plan-abc");
    const req = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse((req?.body as string) ?? "{}");
    expect(body.plan_id).toBe("plan-abc");
  });

  it("validation run sends plan_id", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "j4" }),
    });
    await validationApi.run("plan-abc");
    const req = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]?.[1] as RequestInit | undefined;
    const body = JSON.parse((req?.body as string) ?? "{}");
    expect(body.plan_id).toBe("plan-abc");
  });
});
