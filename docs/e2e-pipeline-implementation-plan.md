# E2E Pipeline Implementation Plan

This document plans the **full pipeline** (import → scan → plan → apply → validate) and **E2E script** so every interface, adapter, and failure mode is covered before building. No ad-hoc patching.

---

## 1. Pipeline flow (fixed)

| Step | API | Use case | Input | Output | Storage |
|------|-----|----------|--------|--------|---------|
| Import | `POST /api/projects/from-git` | (inline in route) | repo_url, branch, name | project_id, root_path | Clone to `/tmp/cloudshift/{name}` |
| Scan | `POST /api/scan` → poll `GET /api/scan/{job_id}` | ScanProjectUseCase | root_path, source/target provider, **project_id** | job_id → result (files, services) | In-memory _results[job_id]; **if project_id set** → DB scan_manifests(project_id) |
| Plan | `POST /api/plan` → poll `GET /api/plan/{job_id}` | GeneratePlanUseCase | project_id, **manifest_id** (= project_id) | job_id → result (plan_id, steps) | In-memory _results[job_id]; **must also** store by plan_id for Apply |
| Apply | `POST /api/apply` → poll `GET /api/apply/{job_id}` | ApplyTransformationUseCase | **plan_id** | job_id → result (diffs, applied_steps) | In-memory _results[job_id] |
| Validate | `POST /api/validate` → poll `GET /api/validate/{job_id}` | ValidateTransformationUseCase | plan_id | job_id → result (passed, issues) | In-memory _results[job_id] |

Constraints:

- **Scan** must receive **project_id** so the result can be stored in `scan_manifests` for Plan.
- **Plan** needs **manifest_store.get_manifest(manifest_id)** → already keyed by project_id in DB.
- **Apply** needs **plan_store.get_plan(plan_id)** → today plan result is only in route `_results[job_id]`, not keyed by plan_id → **gap**.

---

## 2. Use case vs adapter matrix

### 2.1 ScanProjectUseCase

| Port | Expected (protocol) | Container provides | Compatible? | Action |
|------|---------------------|--------------------|-------------|--------|
| **fs** (FileSystemReader) | `async list_files(root: str, exclude?) -> list[str]`; `async read_file(path: str) -> str` | walker: `list_files(root: Path, patterns) -> list[Path]` (sync); `read(path: Path) -> str` (sync) | No (sync, different names/signatures) | **Adapter**: wrap walker in async layer; Path↔str; run sync in `asyncio.to_thread`. |
| **parser** (Parser) | `async detect_language(path, content) -> Language \| None`; `async count_lines(content) -> int` | parser: `parse`, `extract_constructs`, `parse_file` (all sync); no detect_language/count_lines | No | **Adapter**: implement from extension + try parse; count_lines = `len(content.splitlines())`; run sync in thread where needed. |
| **detector** (Detector) | `async detect_services(content, language, provider) -> list[(str, ConfidenceScore)]` | detector: `detect(source, language) -> list[(str,int,int)]` (sync) | No (sync, different return shape) | **Adapter**: wrap detect in thread; map to (svc, ConfidenceScore). |
| **allowed_paths** | list of Path (resolved) | settings.allowed_scan_paths + **must include** git import base | Partially (git base was missing in API path) | **Single source**: GIT_IMPORT_BASE in DI; always append to allowed_paths for Scan (API and container). |

### 2.2 GeneratePlanUseCase

| Port | Expected | Container provides | Compatible? | Action |
|------|----------|--------------------|-------------|--------|
| **manifest_store** | `async get_manifest(manifest_id) -> Manifest \| None` | project_repository: `get_manifest` (async, implemented) | Yes | None. |
| **pattern_engine** | `async match_patterns(file_path, services, source_provider, target_provider) -> list[PatternMatch]` | RustPatternEngineAdapter: `match(source, patterns, language)` (sync, different signature) | No | **Adapter**: implement match_patterns by reading file (via fs), calling match/pattern logic, return list of match-like objects; run in thread and return awaitable. |

### 2.3 ApplyTransformationUseCase

| Port | Expected | Container provides | Compatible? | Action |
|------|----------|--------------------|-------------|--------|
| **plan_store** | `async get_plan(plan_id) -> Plan \| None` | project_repository: no get_plan | No | **Storage**: plan route must store result by plan_id (in-memory or DB). **Adapter**: plan_store must implement get_plan(plan_id). |
| **pattern_engine** | `async apply_pattern(pattern_id, content) -> str` | RustPatternEngineAdapter: `async apply_pattern` | Yes | None. |
| **fs** (FileSystem) | `async read_file(path: str)`; `async write_file(path, content)`; `async copy_file(src, dst)` | LocalFileSystem: `read(path: Path)` (sync); `write` (sync); `copy_file` (sync) | No (sync, Path vs str) | **Adapter**: wrap file_system in async layer; Path↔str; run sync in thread. |
| **diff_engine** | `async compute_diff(original, modified, path) -> list[DiffHunkRaw]` | RustDiffAdapter: check if async/sync | Check | Adapter if sync. |
| **git** | `is_repo_clean(project_path)` (sync) | GitSafety | Yes | None. |

### 2.4 ValidateTransformationUseCase

| Port | Expected | Container provides | Compatible? | Action |
|------|----------|--------------------|-------------|--------|
| (various) | — | container.resolve(ValidateTransformationUseCase) | Assumed OK for now | No change in this plan. |

---

## 3. Single adapter layer (design)

- **Place**: one module under `presentation/api/` or `infrastructure/adapters/` that holds **only** API-facing adapters used to satisfy use case protocols. No business logic.
- **Responsibilities**:
  - **Scan**: Async wrappers for fs (walker), parser, detector so ScanProjectUseCase gets async `list_files`, `read_file`, `detect_language`, `count_lines`, `detect_services` with correct signatures.
  - **Plan**: Adapter that implements `match_patterns(file_path, services, source_provider, target_provider)` using Rust engine + file read (or stub returning [] until full impl).
  - **Apply**: Async wrapper for fs (read_file/write_file/copy_file with str paths); plan_store that can `get_plan(plan_id)` from a shared store.
- **Wiring**: `dependencies.py` (get_scan_use_case, get_plan_use_case, get_apply_use_case) builds use cases with these adapters only. Container stays as-is for CLI/resolve.

---

## 4. Storage and IDs

- **Scan**: Result in `_results[job_id]`; **and** when `project_id` is present, persist to `scan_manifests` (project_id) so Plan can load by manifest_id = project_id. **Done.**
- **Plan**: Result in `_results[job_id]`. **Gap**: Apply needs plan by `plan_id`. So when plan completes, **also** store result in a structure keyed by `plan_id`: e.g. in-memory `_plan_by_id: dict[str, Any]` in plan route, and inject a plan_store adapter that reads from it (or persist to DB). **To implement.**
- **Apply / Validate**: In-memory by job_id only is enough for polling; no cross-step lookup.

---

## 5. Paths and security

- **GIT_IMPORT_BASE** = `/tmp/cloudshift` (single constant in DI; projects.py can import from same place).
- **allowed_scan_paths**: Default in settings = `[".", "data", "/tmp/cloudshift"]`. **Always** append `GIT_IMPORT_BASE` when building Scan use case (both in container and in API dependencies) so macOS `/tmp` → `/private/tmp` is allowed.

---

## 6. E2E script requirements

- **Base URL / auth**: Env `CLOUDSHIFT_BASE_URL`, optional `CLOUDSHIFT_API_KEY` or `CLOUDSHIFT_BEARER_TOKEN`.
- **Import**: POST from-git (AWS + Azure repos). Timeout for POST **600s** (clone can be slow). **Done.**
- **Polling**: GET scan/plan/apply/validate by job_id. **404 = “not ready”**: do **not** raise; retry until 200 or timeout (e.g. 300s). **Done** (script now returns 404 as status and retries).
- **Errors**: On 200, if body has `error`, treat as failed and report.
- **Order**: For each project: scan (with project_id) → poll → plan (project_id, manifest_id=project_id) → poll → apply (plan_id) → poll → validate (plan_id) → poll.

---

## 7. Implementation checklist (order) — DONE

1. **Single adapter module** — **Done**  
   - `cloudshift/presentation/api/scan_adapters.py`: `AsyncScanFs`, `AsyncScanParser`, `AsyncScanDetector`.  
   - `get_scan_use_case` uses them; `allowed_paths` includes `GIT_IMPORT_BASE`.

2. **Plan: pattern_engine and plan store** — **Done**  
   - `plan_adapters.py`: `PlanPatternEngineAdapter` (match_patterns returns [] for now).  
   - `plan_store.py`: in-memory `_plan_by_id`; `register_plan(plan_id, result)` called from plan route on success; `PlanStoreAdapter` for `get_plan(plan_id)`.

3. **Apply: async fs and plan_store** — **Done**  
   - `apply_adapters.py`: `AsyncApplyFs`, `AsyncDiffEngineAdapter`.  
   - `get_apply_use_case` uses `PlanStoreAdapter()`, `AsyncApplyFs(container.file_system)`, `AsyncDiffEngineAdapter(container.diff)`.

4. **E2E script** — **Done**  
   - 404 → retry; long timeout for from-git; see `docs/run-pipeline-e2e.md`.

5. **Tests** — **Done**  
   - `test_get_plan_use_case` updated (container has `project_repository`); background runner tests pass.

---

## 8. Out of scope for this plan

- Validate use case wiring (assumed via container.resolve).
- Full implementation of `match_patterns` (file_path + services → patterns); stub returning [] is acceptable for “pipeline runs without crash”.
- UI changes beyond existing project_id in scan request.
- Cloud Run / IAP for script (auth env vars only).

---

## 9. Success criteria

- E2E script: import two repos (AWS + Azure), run scan for each (with project_id), then plan, then apply, then validate, without “await list”, “Scan not found”, “Manifest not found”, or “Plan not found” due to wiring/timeouts.
- Scan always allows `/tmp/cloudshift` (and resolved path on macOS).
- One place for scan async adapters; one place for plan store and plan pattern_engine adapter; clear checklist for apply async fs and plan_store.
