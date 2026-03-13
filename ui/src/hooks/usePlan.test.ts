/**
 * Unit tests for usePlan: mapPlanResponse (error, warnings, riskLevel, estimatedChanges).
 */

import { describe, it, expect } from "vitest";
import { mapPlanResponse } from "./usePlan";

describe("mapPlanResponse", () => {
  it("maps plan_id and jobId", () => {
    const data = { plan_id: "plan-abc", project_id: "proj1" };
    const result = mapPlanResponse(data, "job-123");
    expect(result.id).toBe("plan-abc");
    expect(result.jobId).toBe("job-123");
    expect(result.manifestId).toBe("proj1");
  });

  it("maps estimated_files_changed to estimatedChanges", () => {
    const data = { plan_id: "p1", project_id: "proj1", estimated_files_changed: 7 };
    const result = mapPlanResponse(data);
    expect(result.estimatedChanges).toBe(7);
  });

  it("maps estimated_confidence to riskLevel: >= 0.8 -> info", () => {
    const data = { plan_id: "p1", project_id: "proj1", estimated_confidence: 0.9 };
    const result = mapPlanResponse(data);
    expect(result.riskLevel).toBe("info");
  });

  it("maps estimated_confidence to riskLevel: >= 0.5 and < 0.8 -> warning", () => {
    const data = { plan_id: "p1", project_id: "proj1", estimated_confidence: 0.6 };
    const result = mapPlanResponse(data);
    expect(result.riskLevel).toBe("warning");
  });

  it("maps estimated_confidence to riskLevel: < 0.5 -> error", () => {
    const data = { plan_id: "p1", project_id: "proj1", estimated_confidence: 0.3 };
    const result = mapPlanResponse(data);
    expect(result.riskLevel).toBe("error");
  });

  it("maps error when present", () => {
    const data = {
      plan_id: "p1",
      project_id: "proj1",
      error: "Manifest m1 not found.",
    };
    const result = mapPlanResponse(data);
    expect(result.error).toBe("Manifest m1 not found.");
  });

  it("maps warnings when present", () => {
    const data = {
      plan_id: "p1",
      project_id: "proj1",
      warnings: ["No patterns matched for main.py", "2 step(s) dropped below threshold"],
    };
    const result = mapPlanResponse(data);
    expect(result.warnings).toHaveLength(2);
    expect(result.warnings).toContain("No patterns matched for main.py");
  });

  it("leaves error and warnings undefined when not in data", () => {
    const data = { plan_id: "p1", project_id: "proj1" };
    const result = mapPlanResponse(data);
    expect(result.error).toBeUndefined();
    expect(result.warnings).toBeUndefined();
  });
});
