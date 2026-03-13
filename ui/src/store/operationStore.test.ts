/**
 * Unit tests for operation store: runPipelineAfterSnippetImport and reset.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useOperationStore } from "./index";

describe("operation store", () => {
  beforeEach(() => {
    useOperationStore.getState().reset();
  });

  it("runPipelineAfterSnippetImport defaults to false", () => {
    expect(useOperationStore.getState().runPipelineAfterSnippetImport).toBe(false);
  });

  it("setRunPipelineAfterSnippetImport sets flag to true", () => {
    useOperationStore.getState().setRunPipelineAfterSnippetImport(true);
    expect(useOperationStore.getState().runPipelineAfterSnippetImport).toBe(true);
  });

  it("reset clears runPipelineAfterSnippetImport", () => {
    useOperationStore.getState().setRunPipelineAfterSnippetImport(true);
    useOperationStore.getState().reset();
    expect(useOperationStore.getState().runPipelineAfterSnippetImport).toBe(false);
  });

  it("reset clears diffs and planResult", () => {
    useOperationStore.getState().setDiffs([{ filePath: "x.py", original: "a", modified: "b", hunks: [], stats: { additions: 1, deletions: 0 } }]);
    useOperationStore.getState().setPlanResult({ id: "p1", manifestId: "m1", transformations: [], stepsByPattern: [], diffs: [], estimatedChanges: 0, riskLevel: "info", timestamp: "" });
    useOperationStore.getState().reset();
    expect(useOperationStore.getState().diffs).toEqual([]);
    expect(useOperationStore.getState().planResult).toBeNull();
  });
});
