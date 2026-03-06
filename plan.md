# CloudShift — Full Alpha Implementation Plan

## Context

CloudShift is an enterprise-grade, air-gapped multi-cloud refactor accelerator that transforms code/IaC from AWS and Azure to GCP. The product is urgent and enterprise-critical. This plan covers the Full Alpha (M1-M2) deliverable across all three surfaces: CLI, Web UI, and VS Code extension.

**Key decisions:**
- **Hybrid architecture**: Rust core (parsing, pattern engine, diffing) + Python application layer (DDD/hexagonal per skill2026)
- **Bridge**: PyO3 + maturin — Rust compiles to native Python module
- **Scope**: 50+ Tier-1 patterns, Python/TypeScript/Terraform/CloudFormation parsers, Refactor + Validation agents, full CLI, Web UI, VS Code extension

**Toolchain**: Rust 1.93, Python 3.13, Node 22, npm. Maturin to be installed.

---

## Monorepo Structure

```
cloudshift/
├── Cargo.toml                       # Rust workspace root
├── pyproject.toml                   # Python project (maturin backend)
├── package.json                     # npm workspace root
├── Makefile                         # Unified build commands
│
├── rust/
│   └── cloudshift-core/             # Rust core library + PyO3 bindings
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs               # PyO3 module entry point
│           ├── bindings.rs          # All #[pyfunction]/#[pyclass] exports
│           ├── parser/              # Tree-sitter: python, typescript, hcl, cfn
│           │   ├── mod.rs
│           │   ├── ast_types.rs     # Unified AstNode, FileAst, Span types
│           │   ├── python_parser.rs
│           │   ├── typescript_parser.rs
│           │   ├── hcl_parser.rs
│           │   └── json_yaml_parser.rs  # CloudFormation
│           ├── detector/            # Cloud service detection (AWS, Azure)
│           │   ├── mod.rs
│           │   ├── detection_types.rs
│           │   ├── aws_detector.rs
│           │   ├── azure_detector.rs
│           │   └── import_resolver.rs
│           ├── pattern_engine/      # Compiled rule catalogue, matcher, transformer, scorer
│           │   ├── mod.rs
│           │   ├── catalogue.rs     # YAML loading + compilation
│           │   ├── matcher.rs
│           │   ├── transformer.rs
│           │   ├── scorer.rs
│           │   └── rules/           # Per-category rule modules
│           │       ├── mod.rs
│           │       ├── compute.rs
│           │       ├── storage.rs
│           │       ├── database.rs
│           │       ├── messaging.rs
│           │       ├── iam.rs
│           │       ├── secrets.rs
│           │       └── iac.rs
│           ├── diff/                # Unified diff + AST diff generation
│           │   ├── mod.rs
│           │   ├── unified_diff.rs
│           │   └── ast_diff.rs
│           ├── manifest/            # MigrationManifest types
│           │   ├── mod.rs
│           │   └── types.rs
│           ├── walker/              # File walking + dependency graph
│           │   ├── mod.rs
│           │   ├── file_walker.rs
│           │   └── dep_graph.rs
│           └── validation/          # AST equivalence + residual reference scan
│               ├── mod.rs
│               ├── ast_equivalence.rs
│               └── residual_scan.rs
│
├── python/
│   └── cloudshift/                  # Python package (skill2026 hexagonal arch)
│       ├── __init__.py
│       ├── py.typed
│       ├── domain/                  # ZERO infra deps
│       │   ├── __init__.py
│       │   ├── entities/
│       │   │   ├── __init__.py
│       │   │   ├── source_file.py
│       │   │   ├── migration_manifest.py
│       │   │   ├── cloud_construct.py
│       │   │   ├── transformation.py
│       │   │   ├── pattern.py
│       │   │   ├── validation_report.py
│       │   │   └── project.py
│       │   ├── value_objects/
│       │   │   ├── __init__.py
│       │   │   ├── confidence_score.py
│       │   │   ├── cloud_service.py
│       │   │   ├── file_path.py
│       │   │   ├── language.py
│       │   │   ├── service_mapping.py
│       │   │   ├── diff_hunk.py
│       │   │   └── severity.py
│       │   ├── events/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── scan_events.py
│       │   │   ├── transform_events.py
│       │   │   ├── validation_events.py
│       │   │   └── pattern_events.py
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── confidence_calculator.py
│       │   │   ├── transformation_planner.py
│       │   │   └── validation_evaluator.py
│       │   └── ports/
│       │       ├── __init__.py
│       │       ├── parser_port.py
│       │       ├── detector_port.py
│       │       ├── pattern_engine_port.py
│       │       ├── diff_port.py
│       │       ├── llm_port.py
│       │       ├── pattern_store_port.py
│       │       ├── file_system_port.py
│       │       ├── validation_port.py
│       │       ├── project_repository_port.py
│       │       ├── event_bus_port.py
│       │       └── embedding_port.py
│       ├── application/
│       │   ├── __init__.py
│       │   ├── use_cases/
│       │   │   ├── __init__.py
│       │   │   ├── scan_project.py
│       │   │   ├── generate_plan.py
│       │   │   ├── apply_transformation.py
│       │   │   ├── validate_transformation.py
│       │   │   ├── manage_patterns.py
│       │   │   └── generate_report.py
│       │   ├── dtos/
│       │   │   ├── __init__.py
│       │   │   ├── scan_dto.py
│       │   │   ├── plan_dto.py
│       │   │   ├── transformation_dto.py
│       │   │   ├── validation_dto.py
│       │   │   ├── pattern_dto.py
│       │   │   └── report_dto.py
│       │   ├── orchestration/
│       │   │   ├── __init__.py
│       │   │   ├── dag_orchestrator.py
│       │   │   ├── refactor_agent.py
│       │   │   └── validation_agent.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── event_dispatcher.py
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── rust_adapters/
│       │   │   ├── __init__.py
│       │   │   ├── parser_adapter.py
│       │   │   ├── detector_adapter.py
│       │   │   ├── pattern_engine_adapter.py
│       │   │   ├── diff_adapter.py
│       │   │   ├── walker_adapter.py
│       │   │   └── validation_adapter.py
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── ollama_adapter.py
│       │   │   ├── vllm_adapter.py
│       │   │   └── null_adapter.py
│       │   ├── pattern_store/
│       │   │   ├── __init__.py
│       │   │   ├── local_store.py
│       │   │   ├── chroma_store.py
│       │   │   └── embedding_adapter.py
│       │   ├── persistence/
│       │   │   ├── __init__.py
│       │   │   ├── project_repository.py
│       │   │   └── sqlite_setup.py
│       │   ├── file_system/
│       │   │   ├── __init__.py
│       │   │   └── local_fs_adapter.py
│       │   ├── validation/
│       │   │   ├── __init__.py
│       │   │   ├── test_runner.py
│       │   │   ├── iac_plan_adapter.py
│       │   │   └── smoke_test_adapter.py
│       │   └── config/
│       │       ├── __init__.py
│       │       ├── dependency_injection.py
│       │       └── settings.py
│       └── presentation/
│           ├── __init__.py
│           ├── cli/
│           │   ├── __init__.py
│           │   ├── main.py
│           │   ├── commands/
│           │   │   ├── __init__.py
│           │   │   ├── scan.py
│           │   │   ├── plan.py
│           │   │   ├── apply.py
│           │   │   ├── validate.py
│           │   │   ├── patterns.py
│           │   │   ├── report.py
│           │   │   └── config.py
│           │   ├── formatters/
│           │   │   ├── __init__.py
│           │   │   ├── json_formatter.py
│           │   │   ├── table_formatter.py
│           │   │   └── diff_formatter.py
│           │   └── progress.py
│           └── api/
│               ├── __init__.py
│               ├── app.py
│               ├── routes/
│               │   ├── __init__.py
│               │   ├── scan.py
│               │   ├── plan.py
│               │   ├── apply.py
│               │   ├── validate.py
│               │   ├── patterns.py
│               │   ├── report.py
│               │   ├── config.py
│               │   └── ws.py
│               ├── middleware/
│               │   ├── __init__.py
│               │   └── cors.py
│               └── schemas/
│                   ├── __init__.py
│                   ├── scan_schema.py
│                   ├── plan_schema.py
│                   ├── apply_schema.py
│                   ├── validation_schema.py
│                   ├── pattern_schema.py
│                   └── report_schema.py
│
├── ui/                              # React 19 + Vite + shadcn/ui + Tailwind + Monaco Editor
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── ui/                  # shadcn/ui components
│       │   ├── layout/             # Sidebar, Header, MainLayout
│       │   ├── manifest/           # ManifestViewer, ConstructRow, ConfidenceBadge
│       │   ├── diff/               # DiffViewer (Monaco), FileTreeDiff
│       │   ├── validation/         # ValidationDashboard, CheckResult, Timeline
│       │   ├── patterns/           # PatternBrowser, PatternCard, PromoteDialog
│       │   ├── config/             # LLMConfigPanel, SettingsPage
│       │   └── report/             # AuditReport, ExportButton
│       ├── hooks/                   # useWebSocket, useScan, usePlan, useApply, useValidation, usePatterns
│       ├── services/                # api.ts (typed fetch client), ws.ts (WebSocket client)
│       ├── store/                   # Zustand: projectStore, scanStore, configStore
│       └── types/                   # manifest.ts, plan.ts, validation.ts, pattern.ts
│
├── vscode-extension/                # VS Code Extension
│   ├── package.json                 # Extension manifest with contributes
│   ├── tsconfig.json
│   ├── esbuild.js
│   └── src/
│       ├── extension.ts             # Activation entry point
│       ├── commands/                # refactorSelection, refactorFile, scanProject, validate
│       ├── providers/               # gutterAnnotation, diff, diagnostics, statusBar
│       ├── client/                  # cloudshiftClient.ts (HTTP to FastAPI)
│       └── views/                   # manifestTreeView, validationPanel
│
├── patterns/                        # YAML pattern catalogue (50+ files)
│   ├── schema.yaml                  # Pattern schema definition
│   ├── aws_to_gcp/
│   │   ├── compute/                 # lambda_to_cloud_functions.yaml, ecs_to_gke.yaml, etc.
│   │   ├── storage/                 # s3_to_gcs.yaml (per-language variants)
│   │   ├── database/               # dynamodb_to_firestore.yaml, rds_to_cloud_sql.yaml, etc.
│   │   ├── messaging/              # sqs_to_pubsub.yaml, sns_to_pubsub.yaml, etc.
│   │   ├── iam/                    # iam_policy_to_cloud_iam.yaml, cognito_to_firebase_auth.yaml
│   │   ├── secrets/                # secrets_manager_to_secret_manager.yaml
│   │   └── iac/                    # terraform_aws_to_gcp.yaml, cloudformation_to_terraform.yaml
│   └── azure_to_gcp/               # mirrors aws_to_gcp structure
│
├── tests/
│   ├── golden/                      # Golden test fixtures
│   │   ├── aws_python/input/ + expected/
│   │   ├── aws_typescript/input/ + expected/
│   │   ├── aws_terraform/input/ + expected/
│   │   └── aws_cloudformation/input/ + expected/
│   ├── integration/                 # E2E: bridge, scan, apply, API
│   └── conftest.py
│
└── docker/
    ├── Dockerfile                   # Multi-stage: Rust build -> Python runtime
    └── docker-compose.yml           # Dev: app + optional Ollama
```

---

## Rust Core — What Gets Built

**Parsers** (tree-sitter): Python, TypeScript, HCL, CloudFormation (serde JSON/YAML). Each produces unified `FileAst` with `AstNode` types (Import, FunctionCall, ClientInit, ResourceBlock, etc.).

**Detectors**: AWS (boto3, @aws-sdk, terraform aws_*, CloudFormation types, env vars, ARNs) and Azure (azure-sdk, azurerm_*, ARM types). Includes import alias resolution.

**Pattern Engine**: Loads YAML rule files from `/patterns/` at startup into compiled `RuleCatalogue`. Matcher finds best rule per construct. Transformer produces replacement text + import changes. Scorer adjusts confidence based on specificity, version match, and usage history.

**Diff**: Unified diff via `similar` crate. AST-level structural diff for validation.

**Walker**: gitignore-respecting directory traversal via `ignore` crate. Dependency graph builder with topological sort.

**Validation**: AST equivalence checker + residual AWS/Azure reference scanner (ARNs, regions, SDK imports).

**PyO3 Bindings**: All above exposed as Python-callable functions via `cloudshift_core` native module. Batch operations release GIL for true parallelism via Rayon. Key exports:
- `parse_file()`, `parse_files_parallel()`
- `detect_constructs()`, `detect_constructs_batch()`
- `match_patterns()`, `transform_construct()`, `transform_file()`
- `generate_diff()`, `generate_manifest()`
- `walk_directory()`, `build_dep_graph()`
- `check_ast_equivalence()`, `scan_residual_references()`
- `load_pattern_catalogue()`
- PyClasses: `PyFileAst`, `PyCloudConstruct`, `PyMatchResult`, `PyTransformOutput`, `PyMigrationManifest`, `PyDiffResult`, `PyValidationResult`

**Key Cargo dependencies**: pyo3 0.28, tree-sitter 0.26, tree-sitter-{python,typescript,hcl}, serde/serde_json/serde_yaml, similar, ignore, rayon, regex, thiserror, pythonize

---

## Python Layer — Architecture per skill2026

**Domain ports** (Protocol classes): `ParserPort`, `DetectorPort`, `PatternEnginePort`, `DiffPort`, `LLMPort`, `PatternStorePort`, `FileSystemPort`, `ValidationPort`, `EmbeddingPort`, `EventBusPort`.

**Domain entities** (frozen dataclasses): `SourceFile`, `MigrationManifest` (aggregate root), `CloudConstruct`, `Transformation`, `Pattern`, `ValidationReport`, `Project` (aggregate root).

**Value objects**: `ConfidenceScore` (0.0-1.0, auto-apply >= 0.85), `CloudProvider` (AWS/AZURE), `CloudService` (all services enum), `Language` (PYTHON/TYPESCRIPT/HCL/etc.), `ServiceMapping`, `DiffHunk`, `Severity`.

**Domain services**: `ConfidenceCalculator`, `TransformationPlanner`, `ValidationEvaluator`.

**Domain events**: `ScanStarted/Completed`, `TransformStarted/Completed/Failed`, `ValidationStarted/Passed/Failed`, `PatternPromoted/Retired`.

**Rust adapters**: Each wraps `cloudshift_core` PyO3 calls behind a domain port. Example: `ParserAdapter.parse_file()` calls `cloudshift_core.parse_file()` and converts to domain `FileAst`.

**Use cases**: `ScanProjectUseCase`, `GeneratePlanUseCase`, `ApplyTransformationUseCase`, `ValidateTransformationUseCase`, `ManagePatternsUseCase`, `GenerateReportUseCase`.

**Orchestration**: `DAGOrchestrator` for parallel-safe workflow execution. `RefactorAgent` (7-step INGEST->COMMIT pipeline). `ValidationAgent` (6 checks — AST+residual in parallel, then SDK surface, optional unit tests + IaC plan, then report).

**Composition root**: Single `Container` class in `infrastructure/config/dependency_injection.py` wires all ports to adapters. Only file that references concrete implementations.

---

## Delivery Surfaces

**CLI** (Typer + Rich): `cloudshift scan|plan|apply|validate|patterns|report|config`. JSON output mode (`--json`). Exit codes: 0/1/2. Rich progress bars + tables. Entry: `cloudshift.presentation.cli.main:app`.

**Web UI** (FastAPI backend + React frontend):
- REST API: POST `/api/scan`, `/api/plan`, `/api/apply`, `/api/validate`. CRUD `/api/patterns`. GET `/api/report/{id}`, `/api/config`.
- WebSocket: `ws://localhost:8000/ws/progress/{operation_id}` for live progress streaming.
- React pages: Dashboard, Manifest Viewer (table + filters + override controls), Diff Viewer (Monaco side-by-side + custom cloud decorators), Validation Dashboard (cards per check + recommendation banner), Pattern Browser (grid + search + promote/retire), LLM Config Panel, Settings, Audit Report (export JSON/CSV/PDF).
- State management: Zustand. Routing: React Router v7.

**VS Code Extension**:
- Commands: refactorSelection, refactorFile, scanProject, showPlan, applyTransformations, validate, showPatterns.
- Context menu: right-click "CloudShift: Refactor Selection/File".
- Gutter annotations: cloud icons on lines with detected constructs, colored by confidence.
- Diff: native VS Code diff via virtual TextDocumentContentProvider.
- Diagnostics: validation results as Problems (warnings for residual refs, errors for failures).
- Status bar: `CloudShift: 42 patterns | 3 LLM calls`.
- Tree views: manifest (file -> constructs), validation results.
- Config: `cloudshift.apiUrl` setting (default `http://localhost:8000`).

---

## Build Order (10 Phases)

| Phase | Days | Deliverable | Dependencies |
|-------|------|-------------|-------------|
| 0. Scaffolding | 1-2 | Monorepo structure, maturin "hello world", test infra | None |
| 1. Rust Parsers + Infra | 3-10 | Tree-sitter parsers (Py/TS/HCL/CFn), walker, diff, manifest | Phase 0 |
| 2. Rust Detectors + Pattern Engine | 5-14 | AWS/Azure detectors, pattern catalogue, matcher, transformer | Phase 1 (ast_types) |
| 3. PyO3 Bindings + Python Domain | 10-16 | bindings.rs, all entities/VOs/events/ports/domain services | Phase 2 |
| 4. Python Infra + Use Cases | 14-22 | Rust adapters, LLM/store/FS adapters, all use cases, agents | Phase 3 |
| 5. CLI | 20-24 | All 7 command groups, formatters, progress | Phase 4 |
| 6. Patterns + Golden Tests | 18-26 | 50+ YAML patterns, golden test fixtures | Phase 2 (parallel) |
| 7. FastAPI Backend | 22-28 | REST routes, WebSocket, schemas | Phase 4 |
| 8. Web UI | 24-34 | React app: all pages + Monaco diff + shadcn/ui | Phase 7 |
| 9. VS Code Extension | 28-36 | Full extension: commands, providers, views | Phase 7 |
| 10. Integration + Polish | 34-40 | E2E tests, perf validation, Docker, docs | All |

Parallelization: Phases 1+1C, 3D+3E, 4F+4G, 6, 8+9 can run concurrently.

---

## Testing Strategy

| Layer | Tool | Coverage Target | Approach |
|-------|------|----------------|----------|
| Rust unit | `cargo test` | >= 90% | Parser, detector, pattern engine, diff, validation |
| Python domain | pytest | >= 95% | Pure logic, no mocks. Entities, VOs, domain services |
| Python application | pytest | >= 80% | Mocked ports via AsyncMock. Use cases, agents |
| Python infrastructure | pytest | integration | Rust adapter bridge tests, LLM/store tests |
| Golden tests | pytest | 50+ cases | Input/expected pairs per language. Full pipeline |
| API tests | pytest + httpx | all endpoints | FastAPI TestClient |
| UI tests | vitest + RTL | key components | Component tests with mock API |
| E2E | pytest | critical paths | Scan->Plan->Apply->Validate full flow |

---

## Key Dependencies

**Rust**: pyo3 0.28, tree-sitter 0.26, tree-sitter-{python,typescript,hcl}, serde, similar, ignore, rayon, regex, thiserror, pythonize

**Python**: maturin >=1.8, typer >=0.15, rich >=14, fastapi >=0.115, uvicorn, pydantic >=2.10, httpx, chromadb >=0.6, pytest, pytest-asyncio, ruff

**UI**: react 19, vite 6, tailwindcss 4, @monaco-editor/react, zustand 5, react-router 7, shadcn/ui

**VS Code**: @types/vscode ^1.96, esbuild, typescript 5.7

---

## Verification Plan

1. **Phase 0**: `maturin develop` succeeds, `python -c "import cloudshift_core"` works, `cargo test` passes
2. **Phase 1-2**: `cargo test` passes all parser/detector/pattern engine tests
3. **Phase 3**: `pytest tests/domain/` passes with >= 95% coverage
4. **Phase 4**: `pytest tests/application/` + `pytest tests/infrastructure/` pass
5. **Phase 5**: `cloudshift scan ./tests/golden/aws_python/input/` produces correct manifest
6. **Phase 6**: `pytest tests/golden/` — all 50+ golden tests pass
7. **Phase 7**: `pytest tests/integration/test_api_endpoints.py` passes
8. **Phase 8**: `npm run build` in `/ui/` succeeds
9. **Phase 9**: `npm run compile` in `/vscode-extension/` succeeds
10. **Phase 10**: Full E2E: scan real boto3 project -> plan -> apply -> validate -> Web UI review -> VS Code verify
