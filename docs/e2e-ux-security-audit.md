# End-to-End, UI/UX & Security Audit

## 1. End-to-end consistency

### Auth flow
- **Demo (Searce ID)**: Backend expects `X-Searce-ID` or `Authorization: Bearer <token>`. UI can pass API key via `window.__CLOUDSHIFT_API_KEY__` or (when implemented) a Searce ID token.
- **Client (password)**: Backend expects `Authorization: Bearer <jwt>`. UI now:
  - Calls `GET /api/auth/mode` on load and stores `auth_mode` / `deployment_mode`.
  - When `auth_mode === "password"` and no stored token, shows **Login** page.
  - On login, `POST /api/auth/login` returns JWT; UI stores it (persisted) and sends `Authorization: Bearer <token>` on all subsequent API requests.
  - On 401, UI clears token so user is sent back to login.

### Cloud provider casing
- Backend scan API expects `source_provider` / `target_provider` as enum (AWS, AZURE, GCP). Schema validator uppercases string values.
- UI sends `activeProject.sourceProvider` (e.g. `"aws"`) → backend uppercases → consistent.
- Import modal (snippet/git/local) uses `source.toUpperCase()` for from-snippet; project stores `sourceProvider: "aws" | "azure""` and target is fixed to GCP.

### Code loading
- **Snippet**: UI calls `POST /api/projects/from-snippet` with name, content, language, source/target provider; backend writes to `data_dir/snippets/<id>/<filename>` and returns `project_id`, `root_path`, `name`. UI creates project with `path: root_path` so scan uses that path.
- **Git / Local**: UI currently simulates (no backend clone/path validation). For full E2E, backend would need a “register project” that accepts repo URL or path and returns a scannable root.

---

## 2. UI/UX

### Implemented
- **Auth gate**: When `auth_mode=password`, login page is shown until user signs in; after login, main app is shown.
- **Deployment mode**: Sidebar shows “Demo (Gemini)” or “Client (Ollama)” and “Gemini” vs “Qwen 2” from `auth_mode` response.
- **Sign out**: When `auth_mode=password`, sidebar has “Sign out” which clears token and returns to login.
- **Cloud-to-cloud**: Import modal restricts source to AWS/Azure and target to GCP only.
- **Snippet import**: Third tab “Code Snippet” with paste area, language, optional filename.

### Implemented (follow-up)
- **Session expired**: Login page shows “Your session expired. Please sign in again.” when token was cleared due to 401 (`authStore.sessionExpired`).
- **Demo token**: See [auth-demo-mode.md](auth-demo-mode.md) for X-Searce-ID and API key.

---

## 3. Security

### Addressed
- **Path traversal (from-snippet)**: Filename is sanitized with `Path(filename).name` so `../../../etc/passwd` becomes `passwd`. Resolved path is checked to be under `project_dir` before write.
- **Auth**: API key only sent when no Bearer token; Bearer preferred when present. Token cleared on 401 in password mode.
- **JWT**: Server-side sign/verify with HMAC-SHA256; expiry enforced. Production should use a strong `CLOUDSHIFT_JWT_SECRET`.
- **Password storage**: Bcrypt used for new hashes; legacy SHA-256 still accepted. See `.env.example` for generating bcrypt hashes.

### Existing
- **Scan path allowlist**: `allowed_scan_paths` restricts which directories can be scanned; snippet dir is under `data_dir`, which is under default allowlist when run from app root.
- **CORS**: Configured via `allowed_origins` in settings.
- **Validation commands**: `allowed_test_commands` whitelist prevents RCE in validation step.

### Implemented
- **Login rate limit**: 5 attempts per IP per minute; 429 with “Too many login attempts” (see `rate_limit.py` and auth route).
- **Scan allowlist**: Default `allowed_scan_paths` includes `Path(".")` and `Path("data")` so snippet projects under `data_dir` are scannable.
- **Password hashing**: Bcrypt (with SHA-256 fallback for legacy hashes). See `.env.example` for generating bcrypt hashes.
- **Gemini key**: [docs/gemini-api-key.md](gemini-api-key.md) for obtaining and securing the key (GitHub Secrets, env, never commit).

### Recommendations
- In production, prefer `auth_mode=password` and avoid `window.__CLOUDSHIFT_API_KEY__`.
