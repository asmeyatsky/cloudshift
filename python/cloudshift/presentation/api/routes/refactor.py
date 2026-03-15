"""Refactor routes: POST /api/refactor/file, POST /api/refactor/selection, POST /api/refactor/project.

Refactor flow: try pattern matching first; only use LLM when no pattern matches.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

from cloudshift.domain.value_objects.types import CloudProvider, Language
from cloudshift.presentation.api.dependencies import get_container
from cloudshift.presentation.api.schemas import (
    RefactorFileRequestBody,
    RefactorProjectRequestBody,
    RefactorResultResponse,
    RefactorSelectionRequestBody,
    RefactorChangeResponse,
)

router = APIRouter(prefix="/api/refactor", tags=["refactor"])


def _detect_services(content: str, source_provider: str) -> list[str]:
    """Detect cloud services used in source code by looking for common API patterns."""
    services = []
    upper = source_provider.upper()
    if upper == "AWS":
        checks = [
            ("s3", ["boto3.client('s3')", 'boto3.client("s3")', "boto3.resource('s3')", 'boto3.resource("s3")', "s3_client", "s3_resource"]),
            ("lambda", ["boto3.client('lambda')", 'boto3.client("lambda")', "lambda_client", "handler(event"]),
            ("dynamodb", ["boto3.client('dynamodb')", "boto3.resource('dynamodb')", "dynamodb", ".Table("]),
            ("sqs", ["boto3.client('sqs')", "sqs_client", "send_message", "receive_message", "QueueUrl"]),
            ("sns", ["boto3.client('sns')", "sns_client", "TopicArn", ".publish("]),
            ("secretsmanager", ["boto3.client('secretsmanager')", "get_secret_value", "SecretId"]),
            ("ec2", ["boto3.client('ec2')", "boto3.resource('ec2')", "ec2_client"]),
            ("ecs", ["boto3.client('ecs')", "ecs_client"]),
            ("rds", ["boto3.client('rds')", "rds_client"]),
            ("cloudwatch", ["boto3.client('cloudwatch')", "put_metric", "cloudwatch"]),
            ("iam", ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "assume_role"]),
        ]
    elif upper == "AZURE":
        checks = [
            ("blob_storage", ["BlobServiceClient", "ContainerClient", "blob_client", "upload_blob", "download_blob"]),
            ("cosmos_db", ["CosmosClient", "cosmos_client", "read_item", "create_item", "query_items"]),
            ("service_bus", ["ServiceBusClient", "ServiceBusMessage", "send_messages", "receive_messages"]),
            ("key_vault", ["SecretClient", "vault_url", "get_secret", "set_secret"]),
            ("functions", ["azure.functions", "HttpRequest", "HttpResponse", "func.HttpRequest"]),
            ("event_hubs", ["EventHubProducerClient", "EventHubConsumerClient", "EventData"]),
            ("sql", ["pyodbc", "azure.sql", "mssql"]),
            ("identity", ["DefaultAzureCredential", "ManagedIdentityCredential"]),
        ]
    else:
        return []
    for service, patterns in checks:
        if any(p in content for p in patterns):
            services.append(service)
    return services


# Map source services to GCP equivalents
_SERVICE_MAP = {
    # AWS
    "s3": "Cloud Storage (GCS)",
    "lambda": "Cloud Functions",
    "dynamodb": "Firestore",
    "sqs": "Cloud Tasks / Pub/Sub",
    "sns": "Pub/Sub",
    "secretsmanager": "Secret Manager",
    "ec2": "Compute Engine",
    "ecs": "Cloud Run",
    "rds": "Cloud SQL",
    "cloudwatch": "Cloud Monitoring",
    "iam": "IAM / Service Accounts",
    # Azure
    "blob_storage": "Cloud Storage (GCS)",
    "cosmos_db": "Firestore",
    "service_bus": "Pub/Sub",
    "key_vault": "Secret Manager",
    "functions": "Cloud Functions",
    "event_hubs": "Pub/Sub",
    "sql": "Cloud SQL",
    "identity": "IAM / Service Accounts",
}

_PACKAGE_MAP = {
    # AWS
    "s3": {"remove": ["boto3"], "install": ["google-cloud-storage"]},
    "lambda": {"remove": [], "install": ["functions-framework"]},
    "dynamodb": {"remove": ["boto3"], "install": ["google-cloud-firestore"]},
    "sqs": {"remove": ["boto3"], "install": ["google-cloud-tasks", "google-cloud-pubsub"]},
    "sns": {"remove": ["boto3"], "install": ["google-cloud-pubsub"]},
    "secretsmanager": {"remove": ["boto3"], "install": ["google-cloud-secret-manager"]},
    "ec2": {"remove": ["boto3"], "install": ["google-cloud-compute"]},
    "rds": {"remove": ["boto3"], "install": ["cloud-sql-python-connector"]},
    "cloudwatch": {"remove": ["boto3"], "install": ["google-cloud-monitoring"]},
    # Azure
    "blob_storage": {"remove": ["azure-storage-blob"], "install": ["google-cloud-storage"]},
    "cosmos_db": {"remove": ["azure-cosmos"], "install": ["google-cloud-firestore"]},
    "service_bus": {"remove": ["azure-servicebus"], "install": ["google-cloud-pubsub"]},
    "key_vault": {"remove": ["azure-keyvault-secrets", "azure-identity"], "install": ["google-cloud-secret-manager"]},
    "functions": {"remove": ["azure-functions"], "install": ["functions-framework"]},
    "event_hubs": {"remove": ["azure-eventhub"], "install": ["google-cloud-pubsub"]},
    "sql": {"remove": ["pyodbc"], "install": ["cloud-sql-python-connector"]},
    "identity": {"remove": ["azure-identity"], "install": ["google-auth"]},
}


def _infer_language(file_path: str) -> Language:
    ext = (Path(file_path).suffix or "").lstrip(".").lower()
    if ext in ("py",):
        return Language.PYTHON
    if ext in ("ts", "tsx", "js", "jsx"):
        return Language.TYPESCRIPT
    if ext in ("tf", "hcl"):
        return Language.HCL
    if ext in ("yaml", "yml", "json") and "template" in file_path.lower():
        return Language.CLOUDFORMATION
    return Language.PYTHON


def _provider_enum(provider: str) -> CloudProvider | None:
    """Map source_provider/target_provider string to CloudProvider."""
    if not provider:
        return None
    u = (provider or "").upper()
    try:
        return CloudProvider(u)
    except (KeyError, ValueError):
        return None


import re as _re

# ── Fast Python-level pattern replacements (no Rust FFI) ──────────────
# Used by the streaming /project endpoint; the /file endpoint still uses the Rust engine.
_AWS_REPLACEMENTS: list[tuple[str, str, str]] = [
    # Imports
    (r'^import boto3$', 'from google.cloud import storage, firestore', 'import'),
    (r'^from boto3\..*', '# removed boto3 import (replaced with google-cloud)', 'import'),
    # S3 client
    (r'''boto3\.client\(["']s3["']\)''', 'storage.Client()', 'client'),
    (r'''boto3\.resource\(["']s3["']\)''', 'storage.Client()', 'client'),
    (r's3_client\.get_object\(Bucket=([^,]+),\s*Key=([^)]+)\)', r'storage.Client().bucket(\1).blob(\2).download_as_bytes()', 'api'),
    (r's3_client\.put_object\(\s*Bucket=([^,]+),\s*Key=([^,]+),\s*Body=([^,)]+)(?:,[^)]*)*\)', r'storage.Client().bucket(\1).blob(\2).upload_from_string(\3)', 'api'),
    (r's3_client\.list_buckets\(\)', 'list(storage.Client().list_buckets())', 'api'),
    # DynamoDB
    (r'''boto3\.resource\(["']dynamodb["']\)''', 'firestore.Client()', 'client'),
    (r'\.Table\(([^)]+)\)', r'.collection(\1)', 'api'),
    (r'\.put_item\(Item=([^)]+)\)', r'.add(\1)', 'api'),
    (r'\.get_item\(Key=([^)]+)\)', r'.document(\1).get()', 'api'),
    (r'\.delete_item\(Key=([^)]+)\)', r'.document(\1).delete()', 'api'),
    # Lambda handler
    (r'def handler\(event, context\)', 'def main(request)', 'function'),
    # SQS
    (r'''boto3\.client\(["']sqs["']\)''', 'pubsub_v1.PublisherClient()', 'client'),
    (r'sqs_client\.send_message\(', '# TODO: pubsub publish(', 'api'),
    (r'sqs_client\.receive_message\(', '# TODO: pubsub pull(', 'api'),
    # SNS
    (r'''boto3\.client\(["']sns["']\)''', 'pubsub_v1.PublisherClient()', 'client'),
    (r'sns_client\.publish\(', '# TODO: pubsub publish(', 'api'),
    # Secrets Manager
    (r'''boto3\.client\(["']secretsmanager["']\)''', 'secretmanager.SecretManagerServiceClient()', 'client'),
    # General
    (r'AWS_ACCESS_KEY_ID', 'GOOGLE_APPLICATION_CREDENTIALS', 'config'),
    (r'AWS_SECRET_ACCESS_KEY', '# use Application Default Credentials', 'config'),
    (r'aws_access_key_id', 'google_application_credentials', 'config'),
]

_AZURE_REPLACEMENTS: list[tuple[str, str, str]] = [
    # Blob Storage
    (r'from azure\.storage\.blob import .*', 'from google.cloud import storage', 'import'),
    (r'from azure\.identity import .*', 'import google.auth', 'import'),
    (r'BlobServiceClient\([^)]*\)', 'storage.Client()', 'client'),
    (r'\.get_container_client\(([^)]+)\)', r'.bucket(\1)', 'api'),
    (r'\.get_blob_client\(([^)]+)\)', r'.blob(\1)', 'api'),
    (r'\.upload_blob\(([^,)]+)(?:,[^)]*)*\)', r'.upload_from_string(\1)', 'api'),
    (r'\.download_blob\(\)', '.download_as_bytes()', 'api'),
    (r'\.list_blobs\(([^)]*)\)', r'.list_blobs(prefix=\1)', 'api'),
    (r'\.delete_blob\(\)', '.delete()', 'api'),
    # Cosmos DB
    (r'from azure\.cosmos import .*', 'from google.cloud import firestore', 'import'),
    (r'CosmosClient\([^)]*\)', 'firestore.Client()', 'client'),
    # Key Vault
    (r'from azure\.keyvault\.secrets import .*', 'from google.cloud import secretmanager', 'import'),
    (r'SecretClient\([^)]*\)', 'secretmanager.SecretManagerServiceClient()', 'client'),
    # Service Bus
    (r'from azure\.servicebus import .*', 'from google.cloud import pubsub_v1', 'import'),
    (r'ServiceBusClient\([^)]*\)', 'pubsub_v1.PublisherClient()', 'client'),
    # Identity
    (r'DefaultAzureCredential\(\)', 'google.auth.default()', 'auth'),
    (r'ManagedIdentityCredential\(\)', 'google.auth.default()', 'auth'),
]

_TF_REPLACEMENTS: list[tuple[str, str, str]] = [
    (r'provider\s+"aws"', 'provider "google"', 'provider'),
    (r'region\s*=\s*"[^"]*"', 'project = "my-gcp-project"\n  region  = "us-central1"', 'config'),
    (r'resource\s+"aws_s3_bucket"', 'resource "google_storage_bucket"', 'resource'),
    (r'resource\s+"aws_lambda_function"', 'resource "google_cloudfunctions_function"', 'resource'),
    (r'resource\s+"aws_dynamodb_table"', 'resource "google_firestore_database"', 'resource'),
    (r'resource\s+"aws_sqs_queue"', 'resource "google_pubsub_topic"', 'resource'),
    (r'resource\s+"aws_iam_role"', 'resource "google_service_account"', 'resource'),
    (r'resource\s+"aws_vpc"', 'resource "google_compute_network"', 'resource'),
    (r'resource\s+"aws_subnet"', 'resource "google_compute_subnetwork"', 'resource'),
    (r'resource\s+"aws_security_group"', 'resource "google_compute_firewall"', 'resource'),
    (r'resource\s+"aws_instance"', 'resource "google_compute_instance"', 'resource'),
    (r'billing_mode\s*=\s*"PAY_PER_REQUEST"', 'type = "FIRESTORE_NATIVE"', 'config'),
    (r'hash_key\s*=\s*"([^"]*)"', '# hash_key managed by Firestore', 'config'),
]


def _fast_pattern_refactor(content: str, source_provider: str, file_path: str) -> str | None:
    """Fast regex-based pattern replacement. No Rust FFI, no hanging."""
    upper = source_provider.upper()
    lang = _infer_language(file_path)

    if lang == Language.HCL:
        replacements = _TF_REPLACEMENTS
    elif upper == "AWS":
        replacements = _AWS_REPLACEMENTS
    elif upper == "AZURE":
        replacements = _AZURE_REPLACEMENTS
    else:
        return None

    modified = content
    applied = 0
    for pattern_re, replacement, _category in replacements:
        new_text = _re.sub(pattern_re, replacement, modified, flags=_re.MULTILINE)
        if new_text != modified:
            modified = new_text
            applied += 1

    if applied > 0 and modified != content:
        logger.info("[fast-patterns] %d replacements applied for %s", applied, file_path)
        return modified
    return None


async def _refactor_with_patterns(
    content: str,
    file_path: str,
    source_provider: str,
    target_provider: str,
    container,
) -> str | None:
    """Try fast Python regex patterns. Falls back quickly, never hangs."""
    if _provider_enum(target_provider) != CloudProvider.GCP:
        return None
    return _fast_pattern_refactor(content, source_provider, file_path)


async def _refactor_with_rust_patterns(
    content: str,
    file_path: str,
    source_provider: str,
    target_provider: str,
    container,
) -> str | None:
    """Original Rust-based pattern refactor. Used by /file endpoint (VS Code).
    WARNING: Can hang on large files. Do not use in streaming endpoint.
    """
    src = _provider_enum(source_provider)
    tgt = _provider_enum(target_provider)
    if src is None or tgt is None:
        return None
    if tgt != CloudProvider.GCP:
        return None
    store = getattr(container, "pattern_store", None)
    engine = getattr(container, "pattern_engine", None)
    if store is None or engine is None:
        return None
    lang = _infer_language(file_path)
    patterns = store.list_all(
        source_provider=src,
        target_provider=tgt,
        language=lang,
    )
    if not patterns:
        return None
    try:
        matches = await asyncio.to_thread(engine.match, content, patterns, lang)
    except Exception:
        return None
    if not matches:
        return None
    modified = content
    for pattern, _line_start, _line_end in matches:
        try:
            modified = await asyncio.to_thread(engine.apply, modified, pattern, lang)
        except Exception:
            continue
    return modified if modified != content else None


def _is_llm_configured(container) -> bool:
    """True if the container has a real LLM (Gemini or Ollama), not NullLLMAdapter."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return False
    return getattr(llm.__class__, "__name__", "") != "NullLLMAdapter"


def _llm_type(container) -> str:
    """Return the LLM adapter class name for diagnostics."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return "None"
    return getattr(llm.__class__, "__name__", "unknown")


def _refactor_instruction(source: str, target: str) -> str:
    """Build a clear migration instruction so the LLM returns GCP code, not the original."""
    base = (
        f"Refactor this {source} code to equivalent {target} (GCP) code. "
        "Preserve behavior and logic. "
        "Use GCP SDKs: for Python use google-cloud-* packages (e.g. google-cloud-storage instead of Azure Blob, google-auth for credentials). "
        "Return ONLY the refactored code in a single fenced code block (e.g. ```python ... ```), no explanation or duplicate original."
    )
    if source == "AZURE":
        base += (
            " For Azure Blob Storage use Google Cloud Storage (google-cloud-storage). "
            "For DefaultAzureCredential use Google Application Default Credentials (google.auth.default)."
        )
    return base


async def _refactor_with_llm(
    content: str,
    file_path: str,
    source_provider: str,
    target_provider: str,
    container,
) -> str:
    """Use LLM to refactor content to GCP. Returns refactored content or raises on failure."""
    llm = getattr(container, "llm", None)
    if llm is None:
        return content
    if getattr(llm, "__class__", None) and getattr(llm.__class__, "__name__", "") == "NullLLMAdapter":
        return content
    source = (source_provider or "AWS").upper()
    target = (target_provider or "GCP").upper()
    instruction = _refactor_instruction(source, target)
    lang = _infer_language(file_path)
    try:
        refactored = await asyncio.wait_for(
            llm.transform_code(content, instruction, lang),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        logger.warning("LLM transform_code timed out after 30s for %s", file_path)
        return content
    out = (refactored or "").strip()
    if not out or out == content:
        raise ValueError(
            "LLM did not return refactored code (empty or unchanged). Check server logs for Gemini errors."
        )
    return out


def _build_changes(original: str, refactored: str) -> list[dict]:
    """Build a list of RefactorChangeResponse-compatible dicts from line diff."""
    orig_lines = original.splitlines()
    ref_lines = refactored.splitlines()
    changes = []
    if original != refactored and (orig_lines or ref_lines):
        if len(orig_lines) <= 1 and len(ref_lines) <= 1:
            changes.append({
                "line": 1,
                "original": original,
                "replacement": refactored,
                "description": "Refactored to GCP",
            })
        else:
            for i, (o, r) in enumerate(zip(orig_lines, ref_lines)):
                if o != r:
                    changes.append({
                        "line": i + 1,
                        "original": o,
                        "replacement": r,
                        "description": "Refactored to GCP",
                    })
            for i in range(len(orig_lines), len(ref_lines)):
                changes.append({
                    "line": i + 1,
                    "original": "",
                    "replacement": ref_lines[i],
                    "description": "Added (GCP)",
                })
            for i in range(len(ref_lines), len(orig_lines)):
                changes.append({
                    "line": i + 1,
                    "original": orig_lines[i],
                    "replacement": "",
                    "description": "Removed",
                })
    return changes


@router.post(
    "/file",
    response_model=RefactorResultResponse,
    summary="Refactor a full file (VS Code)",
)
async def refactor_file(
    body: RefactorFileRequestBody,
    container=Depends(get_container),
) -> RefactorResultResponse:
    """Refactor file content to GCP: try patterns first, then LLM if no pattern matches."""
    logger.info("Refactor file: llm_type=%s", _llm_type(container))
    try:
        refactored = await _refactor_with_patterns(
            body.content,
            body.file_path,
            body.source_provider,
            body.target_provider,
            container,
        )
        if refactored is None:
            refactored = await _refactor_with_llm(
                body.content,
                body.file_path,
                body.source_provider,
                body.target_provider,
                container,
            )
            if refactored == body.content and not _is_llm_configured(container):
                llm_type = _llm_type(container)
                logger.warning("Refactor file: no pattern match and LLM not configured (llm=%s)", llm_type)
                raise HTTPException(
                    status_code=503,
                    detail=f"No pattern matched and LLM is not configured (server llm={llm_type}). Fix: GitHub repo → Settings → Secrets → Actions: set GEMINI_API_KEY, then push to main to redeploy. Or set CLOUDSHIFT_DEPLOYMENT_MODE=demo and CLOUDSHIFT_GEMINI_API_KEY on the server. Get a key at https://aistudio.google.com/apikey",
                )
            if refactored == body.content and _is_llm_configured(container):
                logger.info("Refactor file: LLM configured but no changes produced (returning 200)")
        changes = _build_changes(body.content, refactored)
        return RefactorResultResponse(
            original_file=body.file_path,
            refactored_content=refactored,
            changes=[RefactorChangeResponse(**c) for c in changes],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Refactor file failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Refactor failed: {str(e)[:500]}",
        ) from e


@router.post(
    "/selection",
    response_model=RefactorResultResponse,
    summary="Refactor a selection (VS Code)",
)
async def refactor_selection(
    body: RefactorSelectionRequestBody,
    container=Depends(get_container),
) -> RefactorResultResponse:
    """Refactor selected lines to GCP: try patterns first, then LLM if no pattern matches."""
    logger.info("Refactor selection: llm_type=%s", _llm_type(container))
    try:
        lines = body.content.splitlines()
        start = max(0, body.start_line - 1)
        end = min(len(lines), body.end_line)
        if start >= end:
            refactored_content = body.content
        else:
            selected = "\n".join(lines[start:end])
            refactored_selection = await _refactor_with_patterns(
                selected,
                body.file_path,
                body.source_provider,
                body.target_provider,
                container,
            )
            if refactored_selection is None:
                refactored_selection = await _refactor_with_llm(
                    selected,
                    body.file_path,
                    body.source_provider,
                    body.target_provider,
                    container,
                )
            parts = []
            if start > 0:
                parts.append("\n".join(lines[:start]))
            parts.append(refactored_selection)
            if end < len(lines):
                parts.append("\n".join(lines[end:]))
            refactored_content = "\n".join(parts)
        if refactored_content == body.content and not _is_llm_configured(container):
            llm_type = _llm_type(container)
            logger.warning("Refactor selection: no pattern match and LLM not configured (llm=%s)", llm_type)
            raise HTTPException(
                status_code=503,
                detail=f"No pattern matched and LLM is not configured (server llm={llm_type}). Fix: GitHub repo → Settings → Secrets → Actions: set GEMINI_API_KEY, then push to main to redeploy. Or set CLOUDSHIFT_DEPLOYMENT_MODE=demo and CLOUDSHIFT_GEMINI_API_KEY on the server. Get a key at https://aistudio.google.com/apikey",
            )
        if refactored_content == body.content and _is_llm_configured(container):
            logger.info("Refactor selection: LLM configured but no changes produced (returning 200)")
        changes = _build_changes(body.content, refactored_content)
        return RefactorResultResponse(
            original_file=body.file_path,
            refactored_content=refactored_content,
            changes=[RefactorChangeResponse(**c) for c in changes],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Refactor selection failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Refactor failed: {str(e)[:500]}",
        ) from e


# ---------------------------------------------------------------------------
# Project-wide streaming refactor
# ---------------------------------------------------------------------------

_SCANNABLE_EXTENSIONS = frozenset(
    {"py", "ts", "tsx", "js", "jsx", "tf", "hcl", "json", "yml", "yaml", "bicep"}
)


async def _refactor_project_stream(body: RefactorProjectRequestBody, container):
    """Async generator yielding NDJSON events for project-wide refactor."""
    logger.info("[refactor-stream] STARTING: project_id=%s root_path=%s", body.project_id, body.root_path)
    # Resolve root_path from project_id or body.root_path
    root_path = body.root_path

    # Resolve __demo__/ prefix to the demos/ directory relative to the project root
    if root_path and root_path.startswith("__demo__/"):
        demo_rel = root_path[len("__demo__/"):]
        # Walk up from this file to find the project root (where demos/ lives)
        project_root = Path(__file__).resolve().parents[5]  # routes -> api -> presentation -> cloudshift -> python -> root
        root_path = str(project_root / "demos" / demo_rel)
        logger.info("Resolved demo path: %s", root_path)

    if not root_path:
        repo = getattr(container, "project_repository", None)
        if repo is None:
            yield json.dumps({"type": "error", "message": "No project repository configured"}) + "\n"
            return
        project = repo.get(body.project_id)
        if project is None:
            yield json.dumps({"type": "error", "message": f"Project {body.project_id} not found"}) + "\n"
            return
        root_path = str(project.root_path)

    root = Path(root_path)
    logger.debug("[refactor-stream] Checking dir: %s exists=%s", root_path, root.is_dir())
    if not root.is_dir():
        yield json.dumps({"type": "error", "message": f"Directory not found: {root_path}"}) + "\n"
        return

    # Walk directory for scannable files — use simple rglob to avoid blocking Rust walker
    all_files = [str(p) for p in root.rglob("*") if p.is_file()]
    logger.info("[refactor-stream] Found %d total files", len(all_files))

    scannable = [
        f for f in all_files
        if Path(f).suffix.lstrip(".").lower() in _SCANNABLE_EXTENSIONS
    ]
    total = len(scannable)
    logger.info("[refactor-stream] %d scannable files", total)

    if total == 0:
        yield json.dumps({"type": "complete", "total": 0, "changed": 0, "pattern_count": 0, "llm_count": 0, "skipped": 0, "llm_configured": _is_llm_configured(container)}) + "\n"
        return

    changed_count = 0
    pattern_count = 0
    llm_count = 0
    skipped_count = 0
    all_services: set[str] = set()

    for idx, file_path in enumerate(scannable):
        rel_path = str(Path(file_path).relative_to(root)) if file_path.startswith(str(root)) else file_path

        yield json.dumps({"type": "progress", "file": rel_path, "index": idx, "total": total}) + "\n"

        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("[refactor] Skipping unreadable %s: %s", rel_path, exc)
            skipped_count += 1
            yield json.dumps({"type": "file_result", "file": rel_path, "changed": False, "method": "skipped"}) + "\n"
            continue

        # Detect cloud services in the source content
        file_services = _detect_services(content, body.source_provider)
        logger.debug("[refactor] Processing %s (%d chars, services=%s)", rel_path, len(content), file_services)

        method = "skipped"
        modified = None

        # Try pattern-based refactor
        try:
            logger.debug("[refactor] Pattern matching %s...", rel_path)
            modified = await _refactor_with_patterns(
                content, file_path, body.source_provider, body.target_provider, container,
            )
            if modified is not None:
                method = "pattern"
                logger.info("[refactor] Pattern matched for %s", rel_path)
            else:
                logger.debug("[refactor] No pattern match for %s", rel_path)
        except Exception as exc:
            logger.warning("[refactor] Pattern error for %s: %s", rel_path, exc, exc_info=True)

        # LLM fallback
        if modified is None and _is_llm_configured(container):
            logger.debug("[refactor] Trying LLM for %s...", rel_path)
            try:
                llm_result = await asyncio.wait_for(
                    _refactor_with_llm(
                        content, file_path, body.source_provider, body.target_provider, container,
                    ),
                    timeout=30.0,
                )
                if llm_result != content:
                    modified = llm_result
                    method = "llm"
                    logger.info("[refactor] LLM changed %s", rel_path)
                else:
                    logger.debug("[refactor] LLM returned unchanged for %s", rel_path)
            except asyncio.TimeoutError:
                logger.warning("[refactor] LLM TIMEOUT for %s", rel_path)
            except Exception as exc:
                logger.warning("[refactor] LLM error for %s: %s", rel_path, exc)
        elif modified is None:
            logger.debug("[refactor] No LLM configured, skipping %s", rel_path)

        if modified is not None and modified != content:
            changed_count += 1
            if method == "pattern":
                pattern_count += 1
            elif method == "llm":
                llm_count += 1
            all_services.update(file_services)
            yield json.dumps({
                "type": "file_result",
                "file": rel_path,
                "original": content,
                "modified": modified,
                "changed": True,
                "method": method,
                "services": file_services,
                "confidence": 0.85 if method == "pattern" else 0.70,
            }) + "\n"
        else:
            skipped_count += 1
            yield json.dumps({"type": "file_result", "file": rel_path, "changed": False, "method": "skipped"}) + "\n"

        # Yield control so the event loop stays responsive
        await asyncio.sleep(0)

    # Build package change sets from detected services
    remove_set: set[str] = set()
    install_set: set[str] = set()
    for svc in all_services:
        pkg = _PACKAGE_MAP.get(svc)
        if pkg:
            remove_set.update(pkg["remove"])
            install_set.update(pkg["install"])

    yield json.dumps({
        "type": "complete",
        "total": total,
        "changed": changed_count,
        "pattern_count": pattern_count,
        "llm_count": llm_count,
        "skipped": skipped_count,
        "llm_configured": _is_llm_configured(container),
        "services_migrated": [{"source": svc, "target": _SERVICE_MAP.get(svc, "?")} for svc in sorted(all_services)],
        "package_changes": {"remove": sorted(remove_set), "install": sorted(install_set)},
    }) + "\n"


@router.post("/project", summary="Refactor entire project (streaming NDJSON)")
async def refactor_project(
    body: RefactorProjectRequestBody,
    container=Depends(get_container),
):
    """Stream project-wide refactor results as NDJSON. Each line is a JSON object."""
    return StreamingResponse(
        _refactor_project_stream(body, container),
        media_type="application/x-ndjson",
    )
