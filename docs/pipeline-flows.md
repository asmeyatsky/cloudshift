# Pipeline flows: UI, API, CLI

All three entry points (UI, API, CLI) follow the same ID handoff so that scan → plan → apply → validate work consistently.

## ID glossary

| ID | Meaning | Set by | Used by |
|----|--------|--------|--------|
| **project_id** | Project/scan identity (e.g. from import or UI). Used as manifest key when saving scan results. | UI/API (optional on scan); CLI uses result after scan | Plan: `project_id` + `manifest_id` in request |
| **manifest_id** | Key to load the saved scan manifest. Must equal `project_id` used when the manifest was saved. | Caller (same as project_id in normal flow) | Plan request |
| **plan_id** | Identifies a generated plan. Returned from plan result; stored in plan store for apply. | Backend (plan use case) | Apply request, Validate request |
| **job_id** | Per-operation job (scan/plan/apply/validate). Returned from each POST; used to poll GET until done. | Backend (each route) | Polling GET /api/{scan,plan,apply,validate}/{job_id} |

## API

- **POST /api/scan**  
  Body: `root_path`, `source_provider`, `target_provider`, optional `project_id`, optional `languages`, `exclude_patterns`.  
  If `project_id` is set and scan succeeds, manifest is saved under that id (for plan).  
  Returns: `202` + `job_id`.

- **GET /api/scan/{job_id}**  
  Returns scan result (or 404 until ready). Result includes `project_id` (from use case), `files`, `total_files_scanned`, `services_found`, optional `error`.

- **POST /api/plan**  
  Body: `project_id`, `manifest_id` (must be the id under which manifest was saved, typically = project_id), optional `strategy`, `max_parallel`.  
  Returns: `202` + `job_id`. On success, plan is registered by `plan_id` for apply.

- **GET /api/plan/{job_id}**  
  Returns plan result with `plan_id`, `project_id`, `steps`, `steps_by_pattern` (grouped by pattern for approve-by-pattern), `estimated_files_changed`, etc. Use `plan_id` for apply/validate.

- **POST /api/apply**  
  Body: `plan_id` (from plan result), optional `step_ids`, `dry_run`, `backup`, `check_git_clean`.  
  Returns: `202` + `job_id`. On success, transform metadata may be persisted for validate (when not dry_run and manifest available).

- **GET /api/apply/{job_id}**  
  Returns apply result: `plan_id`, `success`, `applied_steps`, `diffs`, `files_modified`, `errors`.

- **POST /api/validate**  
  Body: `plan_id`, optional check flags, `run_tests`, `test_command`.  
  Returns: `202` + `job_id`. Validate loads transform metadata by `plan_id` (saved after apply).

- **GET /api/validate/{job_id}**  
  Returns validation result: `plan_id`, `passed`, `issues`, etc.

## CLI

- **scan** `cloudshift scan <path>`  
  Runs scan, then saves manifest with `project_id` = scan result’s `project_id`.  
  User uses that `project_id` as both project_id and manifest_id for plan.

- **plan** `cloudshift plan <project_id> <manifest_id>`  
  Typically `manifest_id` = `project_id`. Plan is registered in process (in-memory) by `plan_id`.  
  User uses returned `plan_id` for apply.

- **apply** `cloudshift apply <plan_id>`  
  Loads plan from in-memory store. If apply succeeds and manifest exists, persists transform metadata for validate.

- **validate** `cloudshift validate <plan_id>`  
  Loads transform metadata by `plan_id` and runs checks.

## UI

- Scan: sends `project_id` = `activeProject.id` so manifest is saved under that id. Polls GET scan until done.
- Plan: `planApi.create(activeProject.id, activeProject.id)` (project_id and manifest_id). Polls GET plan; stores result with `id` = `plan_id` and `jobId` = plan job_id (for diffs).
- Apply: `applyApi.start(planResult.id)` (plan_id). Polls GET apply.
- Validate: `runValidation(planResult.id)` (plan_id). Polls GET validate.

## Consistency rules

1. **Manifest** is stored under the id passed as `project_id` on scan (API/CLI). Plan must use that same id as `manifest_id`.
2. **Plan** is stored by `plan_id` (returned from plan result). Apply and validate must use that `plan_id`.
3. **Transform metadata** is stored by `plan_id` after a successful apply (when manifest is available). Validate reads by `plan_id`.
