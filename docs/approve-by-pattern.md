# Approve-by-pattern: human-in-the-loop at scale

## Problem

When a repo has hundreds of files that match migration patterns (e.g. 300 steps), having a human review or approve **each change** is not feasible. We need a way to approve at the **pattern** level so one decision applies to all similar cases.

## Approach

1. **Group steps by pattern**  
   After the plan is generated, steps are grouped by `(pattern_id, description)`. For example:
   - "S3 Client Init → GCS" applied to 50 files
   - "SQS send_message → Pub/Sub" applied to 30 files
   - "Lambda handler → Cloud Functions" applied to 12 files

2. **Expose groups in the API**  
   The plan result includes `steps_by_pattern`: a list of groups, each with:
   - `pattern_id`, `description`
   - `count` (number of steps)
   - `step_ids` (for apply filtering)
   - `file_paths_sample` (e.g. first 5 paths for display)

3. **UI: approve by pattern**  
   - Show the plan as **pattern groups**, not a flat list of 300 steps.
   - For each group: "**S3 Client Init → GCS** (50 files)" with a sample of paths and an **Approve** action.
   - User approves one or more patterns (or "Approve all").
   - Apply runs only for the **step_ids** of approved patterns (or all steps if "Approve all").

4. **Apply**  
   - Today: `POST /apply` with `plan_id` applies all steps.  
   - Optional: extend to `step_ids: list[str]` so the UI can send only the step_ids from approved pattern groups.  
   - If `step_ids` is empty, apply all steps (backward compatible).

## Data already in place

- **Backend**: `PlanResult.steps_by_pattern` and API `steps_by_pattern` in GET plan response.
- **Apply**: Request body has `step_ids: list[str]`. When provided, the apply use case applies only those steps (already implemented). Empty = apply all steps.

## UI work (future)

- Plan result view: show `steps_by_pattern` as cards/sections (pattern name, count, sample paths, Approve button).
- Track "approved pattern IDs" or "approved step_ids"; on "Apply", send either full plan or only approved step_ids.
- Optional: "Approve all" and "Apply all" for power users; per-pattern approval for cautious rollout.

## Summary

Yes, it makes sense: **group changes by pattern, let the user approve at the pattern level, then apply that pattern to all similar cases automatically.** The backend already exposes `steps_by_pattern`; the remaining work is UI and optionally restricting apply to approved `step_ids`.
