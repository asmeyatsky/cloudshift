# CloudShift by Searce Inc

**Secure, Air-gapped AWS/Azure to GCP Migration**

Deterministic, Auditable, End-to-End Refactoring — Your Code Never Leaves Your Network.

![CloudShift Architecture](docs/cloudshift-architecture.jpg)

---

## What is CloudShift?

CloudShift is an enterprise-grade refactoring accelerator that automatically transforms source code and Infrastructure-as-Code from AWS and Azure to Google Cloud Platform. It runs entirely on-premises with zero external API calls, making it ideal for regulated industries — banking, defense, healthcare, and government.

### Key Differentiators

- **Deterministic & Auditable** — Traceable changes with line-by-line audit trail. White-box, not black-box.
- **Full End-to-End** — From detection to production validation. No residual cloud references.
- **Secure by Design** — Zero external API calls. All processing happens inside your network.
- **Hybrid AI Architecture** — 60+ compiled YAML pattern rules (Rust core) with optional local LLM assist via Ollama. The LLM never operates unsupervised.

---

## How It Works

CloudShift uses a five-stage pipeline:

1. **Scan** — Parse source code (Python, TypeScript, Terraform, CloudFormation) using tree-sitter. Detect AWS/Azure service usage with high-confidence pattern matching.
2. **Plan** — Match detected constructs against 60+ migration patterns. Generate a dependency-aware transformation plan with confidence scores.
3. **Apply** — Execute deterministic, repeatable code transformations. Produce unified diffs for every change.
4. **Validate** — AST equivalence checking, residual cloud reference scanning, SDK surface coverage verification, and optional test suite execution.
5. **Report** — Generate auditable migration reports with per-file confidence scores and issue tracking.

---

## Architecture

**Hybrid Rust + Python** — The performance-critical core (parsing, detection, pattern matching, diffing, validation) is written in Rust and exposed to Python via PyO3. The application layer follows hexagonal / clean architecture (DDD) in Python.

```
Rust Core (cloudshift-core)          Python Application Layer
├── Tree-sitter parsers              ├── Domain (entities, value objects, ports)
├── AWS/Azure service detectors      ├── Application (use cases, orchestration)
├── YAML pattern engine              ├── Infrastructure (adapters, LLM, persistence)
├── Unified diff generator           └── Presentation (CLI, REST API, WebSocket)
├── Dependency graph builder
└── AST validation engine
```

### Delivery Surfaces — One Tool for the Whole Team

| Surface | Audience | Description |
|---------|----------|-------------|
| **CLI** | CI/CD Pipelines | `cloudshift scan \| plan \| apply \| validate \| report` with JSON output mode |
| **Web UI** | Architects | React 19 + Monaco Editor diff viewer + real-time WebSocket progress |
| **VS Code Extension** | Developers | Inline annotations, context menu refactoring, diagnostics panel |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Rust 1.75+ (for building the core)
- Node.js 22+ (for Web UI)

### Installation

```bash
# Clone the repository
git clone https://github.com/asmeyatsky/cloudshift.git
cd cloudshift

# Build the Rust core and install the Python package
pip install maturin
maturin develop

# Install Python dependencies
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Scan a project for AWS service usage
cloudshift scan ./my-aws-project --source AWS --target GCP

# Generate a migration plan
cloudshift plan <project-id> <manifest-id>

# Apply transformations (dry run first)
cloudshift apply <plan-id> --dry-run

# Apply for real
cloudshift apply <plan-id>

# Validate the result
cloudshift validate <plan-id>

# Generate an audit report
cloudshift report <project-id>
```

---

## Supported Migrations

### Languages

| Language | Source Formats | Status |
|----------|---------------|--------|
| Python | boto3, azure-sdk | Full support |
| TypeScript | @aws-sdk, @azure | Full support |
| Terraform HCL | aws_*, azurerm_* | Full support |
| CloudFormation | JSON/YAML templates | Full support |

### Service Mappings (60+ patterns)

| AWS / Azure | GCP Equivalent |
|-------------|----------------|
| S3 / Blob Storage | Cloud Storage |
| DynamoDB / Cosmos DB | Firestore or Bigtable |
| Lambda / Functions | Cloud Functions or Cloud Run |
| SQS / Service Bus | Pub/Sub |
| SNS | Pub/Sub (push subscriptions) |
| Secrets Manager / Key Vault | Secret Manager |
| RDS / Azure SQL | Cloud SQL |
| ElastiCache / Redis Cache | Memorystore |
| ECS/EKS / AKS | GKE or Cloud Run |
| CloudFormation / ARM | Deployment Manager or Terraform |
| CloudWatch / Monitor | Cloud Monitoring + Logging |
| IAM / Azure AD | Cloud IAM |

---

## Optional: LLM-Assisted Transforms

CloudShift includes optional local LLM integration via [Ollama](https://ollama.ai) for edge cases outside the pattern catalogue. The LLM runs entirely on your machine — no data leaves your network.

```bash
# Install Ollama and pull the recommended model
brew install ollama
ollama pull qwen2.5-coder:14b

# Enable in CloudShift
cloudshift config set llm.enabled true
cloudshift config set llm.model qwen2.5-coder:14b
```

See [docs/ollama-integration.md](docs/ollama-integration.md) for air-gapped deployment, Docker setup, and model fine-tuning.

---

## Development

### Running Tests

```bash
# Rust unit tests (31 tests)
cargo test --lib

# Python test suite (690 tests, 99.9% coverage)
python -m pytest tests/ -q

# Coverage report
python -m coverage run --source=python/cloudshift -m pytest tests/
python -m coverage report --show-missing
```

### Project Structure

```
cloudshift/
├── rust/cloudshift-core/     # Rust core (parsers, detectors, pattern engine)
├── python/cloudshift/        # Python application (hexagonal architecture)
│   ├── domain/               # Entities, value objects, ports (zero dependencies)
│   ├── application/          # Use cases, orchestration agents, DTOs
│   ├── infrastructure/       # Rust adapters, LLM, persistence, file system
│   └── presentation/         # CLI (Typer), REST API (FastAPI), WebSocket
├── ui/                       # React 19 + Vite + shadcn/ui Web UI
├── vscode-extension/         # VS Code extension
├── patterns/                 # 60+ YAML migration pattern rules
├── tests/                    # 690+ tests across all layers
├── docker/                   # Dockerfile + docker-compose.yml
└── docs/                     # Ollama integration, architecture docs
```

### Build Commands

```bash
make build          # Build Rust core + Python package
make test           # Run all tests
make lint           # Run ruff linter
make ui             # Build Web UI (npm run build)
make vscode         # Build VS Code extension
make docker         # Build Docker image
```

---

## Deployment

### On-Premises / Air-Gapped

CloudShift is designed for air-gapped environments:

1. Build the distribution on a machine with internet access
2. Transfer via USB or secure file transfer
3. Deploy with Docker or install directly
4. Optionally include the Ollama model bundle (see [scripts/export-model.sh](scripts/export-model.sh))

### Docker

```bash
docker compose up -d    # Starts CloudShift + optional Ollama
```

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| Disk | 20 GB free | 50 GB free |
| GPU | Not required | NVIDIA 16+ GB VRAM (for LLM) |

---

## License

Proprietary — Searce Inc. All rights reserved.
