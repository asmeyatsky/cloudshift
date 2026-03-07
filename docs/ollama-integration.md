# CloudShift — Ollama & LLM Integration Guide

## Overview

CloudShift uses a **hybrid architecture** for code transformation:

1. **Deterministic Pattern Engine** (Rust core) — Handles all 60+ catalogued patterns with zero LLM dependency. This is the primary transformation path and produces auditable, repeatable results with explicit confidence scores.

2. **LLM-Assisted Transformation** (Ollama) — Optional but recommended. Handles edge cases that fall outside the pattern catalogue: unusual API usage patterns, custom abstractions wrapping cloud SDKs, complex business logic interleaved with cloud calls, and confidence assessment for ambiguous transforms.

The LLM never operates unsupervised — all LLM-suggested transforms are flagged with lower confidence scores and require human review in the UI or CLI validation step.

---

## Architecture

```
                    +-------------------+
                    |   CloudShift CLI  |
                    |   Web UI / VSCode |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Python Use Cases |
                    |  (Application)    |
                    +---+----------+----+
                        |          |
           +------------+          +-------------+
           |                                     |
  +--------v---------+              +------------v-----------+
  |  Rust Core        |              |  Ollama Adapter        |
  |  (Pattern Engine) |              |  (LLM Port)           |
  |  Deterministic    |              |  Optional, air-gapped  |
  |  60+ YAML rules   |              |  Local inference only  |
  +---------+---------+              +------------+-----------+
            |                                     |
            |                        +------------v-----------+
            |                        |  Ollama Server          |
            |                        |  localhost:11434        |
            |                        |  qwen2.5-coder:14b     |
            |                        +-------------------------+
            |
  +---------v---------+
  |  Tree-sitter       |
  |  Parsers           |
  +--------------------+
```

---

## Model Selection

### Recommended: `qwen2.5-coder:14b`

| Property | Value |
|---|---|
| Model | Qwen 2.5 Coder 14B (Q4_K_M quantization) |
| Size on disk | ~9 GB |
| RAM required | 12-16 GB |
| GPU | Optional (runs on CPU, faster with GPU) |
| Context window | 32,768 tokens |
| Languages | Python, TypeScript, HCL, JSON, YAML, and 90+ others |
| License | Apache 2.0 (commercial use permitted) |

### Why this model

- **Best-in-class coding performance** at the 14B parameter tier (HumanEval, MBPP, MultiPL-E benchmarks)
- **Multi-language support** — critical for CloudShift which handles Python, TypeScript, Terraform HCL, and CloudFormation simultaneously
- **Long context window** (32K tokens) — handles large files with multiple cloud constructs
- **Apache 2.0 license** — safe for enterprise/commercial distribution
- **Quantized (Q4_K_M)** — 4-bit quantization keeps RAM usage manageable without significant quality loss

### Alternative models

| Model | Size | RAM | When to use |
|---|---|---|---|
| `qwen2.5-coder:7b` | 4.5 GB | 6-8 GB | Resource-constrained environments, laptops with 8 GB RAM |
| `qwen2.5-coder:32b` | 18 GB | 24+ GB | Maximum quality, GPU-equipped servers |
| `codellama:13b` | 7.4 GB | 10 GB | Fallback if Qwen is unavailable |
| `deepseek-coder-v2:16b` | 9 GB | 12 GB | Alternative with strong reasoning |

---

## Installation

### Prerequisites

- **Ollama** runtime (v0.17+)
- **RAM**: minimum 12 GB available (16 GB total system RAM recommended)
- **Disk**: 10 GB free for model weights
- **OS**: macOS (Apple Silicon or Intel), Linux (x86_64, ARM64), Windows via WSL2

### Step 1: Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows (WSL2):**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Step 2: Start Ollama server

```bash
# Foreground (for testing)
ollama serve

# Background service (macOS)
brew services start ollama

# Background service (Linux systemd)
sudo systemctl enable ollama
sudo systemctl start ollama
```

### Step 3: Pull the model

**Online (with internet access):**
```bash
ollama pull qwen2.5-coder:14b
```

**Air-gapped (from exported bundle):**
```bash
# On the machine with internet, export:
ollama cp qwen2.5-coder:14b cloudshift-coder
ollama push cloudshift-coder  # to local registry, or:

# Alternative: copy the blob files directly
# Source machine:
tar -czf cloudshift-model.tar.gz ~/.ollama/models/

# Target (air-gapped) machine:
tar -xzf cloudshift-model.tar.gz -C ~/
ollama list  # should show qwen2.5-coder:14b
```

### Step 4: Verify

```bash
ollama run qwen2.5-coder:14b "Write a Python function that converts boto3 S3 client calls to google-cloud-storage. Just the function signature."
```

---

## Air-Gapped Deployment

This is the critical path for enterprise clients without internet access.

### Packaging the model for transfer

On a machine with internet access:

```bash
# 1. Pull the model
ollama pull qwen2.5-coder:14b

# 2. Find where Ollama stores model blobs
#    macOS: ~/.ollama/models/
#    Linux: /usr/share/ollama/.ollama/models/
ls ~/.ollama/models/blobs/

# 3. Create a portable archive
tar -czf cloudshift-ollama-bundle.tar.gz \
    -C ~/.ollama models/

# 4. Also package the Ollama binary itself
#    macOS: copy from /usr/local/bin/ollama
#    Linux: copy from /usr/local/bin/ollama
cp $(which ollama) ./ollama-binary
tar -czf cloudshift-ollama-complete.tar.gz \
    ollama-binary \
    -C ~/.ollama models/

# 5. Expected bundle size: ~9.5 GB
ls -lh cloudshift-ollama-complete.tar.gz
```

### Installing on air-gapped target

```bash
# 1. Transfer cloudshift-ollama-complete.tar.gz via USB/secure transfer

# 2. Extract
mkdir -p ~/.ollama
tar -xzf cloudshift-ollama-complete.tar.gz -C ~/.ollama
mv ~/.ollama/ollama-binary /usr/local/bin/ollama
chmod +x /usr/local/bin/ollama

# 3. Start and verify
ollama serve &
ollama list
# Should show: qwen2.5-coder:14b
```

### Docker-based deployment (recommended for clients)

The included `docker-compose.yml` handles everything:

```yaml
# docker/docker-compose.yml already includes:
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

  cloudshift:
    build: .
    environment:
      - CLOUDSHIFT_OLLAMA_URL=http://ollama:11434
    depends_on:
      - ollama
```

For air-gapped Docker deployment:
```bash
# On internet-connected machine:
docker pull ollama/ollama:latest
docker save ollama/ollama:latest -o ollama-image.tar

# Build CloudShift image
docker compose build
docker save cloudshift-app:latest -o cloudshift-image.tar

# Transfer both .tar files + the model bundle

# On air-gapped machine:
docker load -i ollama-image.tar
docker load -i cloudshift-image.tar
docker compose up -d

# Load model into running Ollama container:
docker cp cloudshift-ollama-bundle.tar.gz cloudshift-ollama-1:/tmp/
docker exec cloudshift-ollama-1 tar -xzf /tmp/cloudshift-ollama-bundle.tar.gz -C /root/.ollama/
docker exec cloudshift-ollama-1 ollama list
```

---

## CloudShift Integration

### Configuration

CloudShift reads LLM settings from environment variables or `settings.yaml`:

```bash
# Environment variables
export CLOUDSHIFT_OLLAMA_URL=http://localhost:11434
export CLOUDSHIFT_OLLAMA_MODEL=qwen2.5-coder:14b
export CLOUDSHIFT_LLM_ENABLED=true
export CLOUDSHIFT_LLM_TIMEOUT=120
export CLOUDSHIFT_LLM_MAX_TOKENS=4096
```

Or via the CLI:
```bash
cloudshift config set llm.enabled true
cloudshift config set llm.ollama_url http://localhost:11434
cloudshift config set llm.model qwen2.5-coder:14b
```

Or via the Web UI: Settings > LLM Configuration.

### How the LLM is used in the pipeline

#### 1. Pattern Fallback (Scan/Plan phase)

When the deterministic pattern engine can't find a matching rule for a detected cloud construct, the LLM is consulted:

```
Detected: boto3.client('mediaconvert')  -- No YAML pattern exists
    |
    v
LLM Prompt: "Given this AWS MediaConvert SDK usage, suggest the
equivalent GCP Transcoder API code. Include import changes."
    |
    v
Result: Suggested transform with confidence 0.55 (LLM-assisted)
        vs. typical pattern engine confidence of 0.85-0.95
```

#### 2. Confidence Assessment (Plan phase)

The LLM reviews pattern-matched transforms and adjusts confidence:

```
Pattern says: Replace boto3.client('s3') with storage.Client()
              Base confidence: 0.92

LLM reviews surrounding code context:
  - "This code uses S3 Transfer Acceleration" (not supported in GCS)
  - Adjusted confidence: 0.72
  - Added note: "Transfer Acceleration has no GCS equivalent.
    Consider using GCS XML API with custom endpoint."
```

#### 3. Complex Refactoring (Apply phase)

For constructs that span multiple lines or involve business logic:

```python
# Original (complex case)
s3 = boto3.client('s3')
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket='my-bucket', Prefix='data/'):
    for obj in page['Contents']:
        process(obj['Key'], obj['Size'])

# LLM produces the full equivalent:
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('my-bucket')
for blob in bucket.list_blobs(prefix='data/'):
    process(blob.name, blob.size)
```

#### 4. Validation Enhancement (Validate phase)

The LLM checks semantic equivalence beyond AST-level comparison:

```
AST check: PASS (structure equivalent)
Residual scan: PASS (no AWS/Azure references)
LLM semantic check: WARNING
  "Original uses S3 server-side encryption (SSE-KMS).
   Transformed code does not configure CMEK encryption
   on the GCS bucket. Consider adding encryption config."
```

### Python adapter implementation

The Ollama adapter lives at `python/cloudshift/infrastructure/llm/ollama_adapter.py`:

```python
# Key methods:
class OllamaAdapter:
    async def complete(self, prompt: str) -> str
    async def transform_code(self, source: str, context: dict) -> str
    async def assess_confidence(self, original: str, transformed: str) -> float
```

It communicates with Ollama via HTTP (`POST http://localhost:11434/api/generate`).

The `NullLLMAdapter` at `infrastructure/llm/null_adapter.py` is the default when Ollama is not configured — it returns empty responses, so the system degrades gracefully to pattern-engine-only mode.

### Dependency injection

In `infrastructure/config/dependency_injection.py`, the container auto-detects Ollama availability:

```python
@property
def llm(self):
    if self._settings.llm_enabled:
        try:
            return OllamaAdapter(
                url=self._settings.ollama_url,
                model=self._settings.ollama_model,
            )
        except ConnectionError:
            logger.warning("Ollama not reachable, falling back to NullLLM")
    return NullLLMAdapter()
```

---

## Performance Characteristics

### Inference speed (approximate)

| Hardware | Model | Tokens/sec | Typical transform time |
|---|---|---|---|
| Apple M1 (16 GB) | 14B Q4 | 15-25 tok/s | 3-8 seconds |
| Apple M2/M3 Pro (18+ GB) | 14B Q4 | 25-40 tok/s | 2-5 seconds |
| Intel i7 + 32 GB (CPU only) | 14B Q4 | 5-10 tok/s | 8-20 seconds |
| NVIDIA A10G (24 GB VRAM) | 14B Q4 | 60-100 tok/s | 1-2 seconds |
| NVIDIA T4 (16 GB VRAM) | 14B Q4 | 40-60 tok/s | 1-3 seconds |

### Resource usage during operation

- **Idle**: Ollama keeps the model loaded in RAM for 5 minutes (configurable via `OLLAMA_KEEP_ALIVE`)
- **Active inference**: ~12 GB RAM, 100% of one CPU core (or GPU)
- **CloudShift typical session**: 20-50 LLM calls for a medium project (200 files, 30 cloud constructs without pattern matches)

### Batching

CloudShift batches LLM requests to minimize cold-start overhead:
- Groups constructs by file
- Sends context-rich prompts (surrounding code, imports, detected patterns)
- Caches responses to avoid duplicate queries for identical constructs

---

## Custom Model Fine-Tuning (Advanced)

For clients with specific cloud migration patterns not covered by the catalogue, a fine-tuned model can improve accuracy:

### Creating a Modelfile

```dockerfile
# cloudshift.Modelfile
FROM qwen2.5-coder:14b

SYSTEM """You are a cloud migration expert specializing in transforming code
from AWS and Azure to Google Cloud Platform. You produce exact, working code
replacements with correct import statements. You never invent APIs that don't
exist. You always preserve the original code's business logic and error handling.
When uncertain, you say so and suggest manual review."""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 32768
PARAMETER stop "<|endoftext|>"
```

```bash
ollama create cloudshift-coder -f cloudshift.Modelfile
ollama run cloudshift-coder "Convert this boto3 code to GCP..."
```

### Fine-tuning with migration examples

For organizations with historical migration data:

1. Collect before/after code pairs from past migrations
2. Format as instruction-tuning dataset (JSONL)
3. Use Ollama's GGUF import to load a fine-tuned model

This is optional and only recommended for organizations with 100+ validated migration examples.

---

## Troubleshooting

### Ollama server not reachable

```bash
# Check if running
curl http://localhost:11434/api/tags
# If not: ollama serve

# Check CloudShift config
cloudshift config show llm
```

### Out of memory

```bash
# Reduce context size
export OLLAMA_NUM_CTX=8192  # default is 32768

# Or switch to smaller model
ollama pull qwen2.5-coder:7b
cloudshift config set llm.model qwen2.5-coder:7b
```

### Slow inference on CPU

```bash
# Verify GPU is being used (macOS)
ollama ps
# Should show "metal" or "cuda" in the processor column

# If stuck on CPU, try restarting
ollama stop qwen2.5-coder:14b
ollama run qwen2.5-coder:14b "test"
```

### Model not producing useful output

The system prompt and temperature matter. CloudShift's adapter uses `temperature: 0.1` for deterministic output. If you're getting creative/wrong answers:

```bash
cloudshift config set llm.temperature 0.05
```

---

## Client Deployment Checklist

- [ ] Ollama binary installed on target machine
- [ ] Model weights transferred and loaded (`ollama list` shows model)
- [ ] `ollama serve` running (or Docker container up)
- [ ] CloudShift configured with correct Ollama URL
- [ ] Health check passes: `cloudshift config show llm` shows `connected: true`
- [ ] Test transform works: `cloudshift scan --source AWS --target GCP ./test-project/`
- [ ] Document client's hardware specs for support reference
- [ ] Provide client with this guide for model management

### Minimum hardware requirements (document for clients)

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| Disk | 20 GB free | 50 GB free |
| GPU | Not required | NVIDIA with 16+ GB VRAM |
| OS | Ubuntu 22.04+ / macOS 13+ / Windows 11 (WSL2) | Ubuntu 24.04 / macOS 14+ |
