/**
 * Unit tests for useApply: buildFileDiffsFromApplyResult and demo fallback behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { buildFileDiffsFromApplyResult } from "./useApply";

describe("buildFileDiffsFromApplyResult", () => {
  it("returns empty array when modified_file_details is missing", () => {
    expect(buildFileDiffsFromApplyResult({})).toEqual([]);
    expect(buildFileDiffsFromApplyResult({ plan_id: "p1" })).toEqual([]);
  });

  it("returns empty array when modified_file_details is empty", () => {
    expect(buildFileDiffsFromApplyResult({ modified_file_details: [] })).toEqual([]);
  });

  it("returns empty array when modified_file_details is not an array", () => {
    expect(buildFileDiffsFromApplyResult({ modified_file_details: null })).toEqual([]);
    expect(buildFileDiffsFromApplyResult({ modified_file_details: {} })).toEqual([]);
  });

  it("maps one file to FileDiff with path, original, modified, stats", () => {
    const data = {
      modified_file_details: [
        {
          path: "src/main.py",
          original_content: "import boto3\nx = 1",
          modified_content: "from google.cloud import storage\nx = 1",
        },
      ],
    };
    const diffs = buildFileDiffsFromApplyResult(data);
    expect(diffs).toHaveLength(1);
    expect(diffs[0].filePath).toBe("src/main.py");
    expect(diffs[0].original).toBe("import boto3\nx = 1");
    expect(diffs[0].modified).toBe("from google.cloud import storage\nx = 1");
    expect(diffs[0].hunks).toEqual([]);
    expect(diffs[0].stats.additions).toBeGreaterThanOrEqual(0);
    expect(diffs[0].stats.deletions).toBeGreaterThanOrEqual(0);
  });

  it("handles multiple files", () => {
    const data = {
      modified_file_details: [
        { path: "a.py", original_content: "a", modified_content: "a'" },
        { path: "b.ts", original_content: "b", modified_content: "b'" },
      ],
    };
    const diffs = buildFileDiffsFromApplyResult(data);
    expect(diffs).toHaveLength(2);
    expect(diffs[0].filePath).toBe("a.py");
    expect(diffs[1].filePath).toBe("b.ts");
  });

  it("uses empty string when content fields are missing", () => {
    const data = {
      modified_file_details: [{ path: "f.py" }],
    };
    const diffs = buildFileDiffsFromApplyResult(data);
    expect(diffs[0].original).toBe("");
    expect(diffs[0].modified).toBe("");
  });
});
