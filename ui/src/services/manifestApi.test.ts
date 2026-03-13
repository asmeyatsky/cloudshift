/**
 * Tests for Fix 3: manifestApi calls real backend instead of returning hardcoded stub.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { manifestApi } from "./api";

describe("manifestApi.get (Fix 3)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("calls GET /api/manifest with project_id query param", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { file: "src/main.py", patterns: [], status: "pending" },
        { file: "src/db.py", patterns: [], status: "scanned" },
      ],
    });

    const result = await manifestApi.get("proj-42");

    expect(fetch).toHaveBeenCalledWith(
      "/api/manifest?project_id=proj-42",
      expect.objectContaining({ method: "GET" }),
    );
    expect(result.success).toBe(true);
    if (!result.success) return;

    expect(result.data.projectId).toBe("proj-42");
    expect(result.data.entries).toHaveLength(2);
    expect(result.data.entries[0].filePath).toBe("src/main.py");
    expect(result.data.entries[0].status).toBe("pending");
    expect(result.data.entries[1].filePath).toBe("src/db.py");
    expect(result.data.entries[1].status).toBe("scanned");
    expect(result.data.summary.totalEntries).toBe(2);
    expect(result.data.summary.byStatus.pending).toBe(1);
    expect(result.data.summary.byStatus.scanned).toBe(1);
  });

  it("returns failure when backend returns error", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({ detail: "Database error" }),
    });

    const result = await manifestApi.get("proj-99");
    expect(result.success).toBe(false);
  });

  it("returns empty entries when backend returns empty array", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    const result = await manifestApi.get("proj-empty");
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.data.entries).toHaveLength(0);
    expect(result.data.summary.totalEntries).toBe(0);
  });

  it("encodes special characters in project_id", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    await manifestApi.get("proj with spaces & special=chars");
    expect(fetch).toHaveBeenCalledWith(
      "/api/manifest?project_id=proj%20with%20spaces%20%26%20special%3Dchars",
      expect.anything(),
    );
  });
});
