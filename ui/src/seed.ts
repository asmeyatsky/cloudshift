import type {
  ApplyResult,
  Project,
  ManifestEntry,
  ScanResult,
  PlanResult,
  FileDiff,
  ValidationResult,
  Pattern,
} from "./types";

/* ------------------------------------------------------------------ */
/*  Demo project                                                       */
/* ------------------------------------------------------------------ */

export const SEED_PROJECT: Project = {
  id: "proj-a1b2c3d4",
  name: "payments-service",
  path: "demos/aws_python_microservice/input",
  sourceProvider: "aws",
  targetProvider: "gcp",
  config: {
    excludePaths: ["node_modules/**", ".git/**", "dist/**"],
    includePatterns: ["**/*.py", "**/*.ts", "**/*.tf", "**/*.yaml"],
    autoValidate: true,
    dryRun: false,
    maxConcurrency: 4,
  },
  createdAt: "2026-03-06T10:00:00Z",
  updatedAt: "2026-03-08T14:22:00Z",
};

/* ------------------------------------------------------------------ */
/*  Manifest entries                                                   */
/* ------------------------------------------------------------------ */

export const SEED_ENTRIES: ManifestEntry[] = [
  {
    id: "e-001",
    filePath: "src/handlers/payment_processor.py",
    resourceType: "Lambda Function",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "validated",
    transformations: [
      { id: "t-001", patternId: "p-lambda-cf", patternName: "Lambda → Cloud Functions", filePath: "src/handlers/payment_processor.py", lineStart: 1, lineEnd: 45, before: "", after: "", confidence: 0.94, status: "applied" },
      { id: "t-002", patternId: "p-boto3-s3", patternName: "boto3 S3 → google-cloud-storage", filePath: "src/handlers/payment_processor.py", lineStart: 12, lineEnd: 18, before: "", after: "", confidence: 0.91, status: "applied" },
    ],
    issues: [],
    metadata: { runtime: "python3.11", memory: 512, timeout: 30 },
    createdAt: "2026-03-06T10:05:00Z",
    updatedAt: "2026-03-08T14:10:00Z",
  },
  {
    id: "e-002",
    filePath: "src/handlers/notification_sender.py",
    resourceType: "Lambda Function",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "validated",
    transformations: [
      { id: "t-003", patternId: "p-lambda-cf", patternName: "Lambda → Cloud Functions", filePath: "src/handlers/notification_sender.py", lineStart: 1, lineEnd: 38, before: "", after: "", confidence: 0.92, status: "applied" },
      { id: "t-004", patternId: "p-sns-pubsub", patternName: "SNS → Pub/Sub", filePath: "src/handlers/notification_sender.py", lineStart: 22, lineEnd: 30, before: "", after: "", confidence: 0.88, status: "applied" },
    ],
    issues: [],
    metadata: { runtime: "python3.11", memory: 256, timeout: 15 },
    createdAt: "2026-03-06T10:05:00Z",
    updatedAt: "2026-03-08T14:12:00Z",
  },
  {
    id: "e-003",
    filePath: "src/services/queue_consumer.py",
    resourceType: "SQS Queue",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "applied",
    transformations: [
      { id: "t-005", patternId: "p-sqs-pubsub", patternName: "SQS → Cloud Tasks", filePath: "src/services/queue_consumer.py", lineStart: 5, lineEnd: 52, before: "", after: "", confidence: 0.87, status: "applied" },
    ],
    issues: [
      { id: "i-001", entryId: "e-003", filePath: "src/services/queue_consumer.py", line: 34, column: 8, severity: "warning", code: "DEAD_LETTER_QUEUE", message: "SQS dead-letter queue configuration has no direct Cloud Tasks equivalent. Consider using Pub/Sub dead-letter topics.", suggestion: "Use google.cloud.pubsub_v1 with dead_letter_policy for retry handling", ruleId: "sqs-dlq-mapping" },
    ],
    metadata: { queueType: "FIFO", visibilityTimeout: 60 },
    createdAt: "2026-03-06T10:06:00Z",
    updatedAt: "2026-03-08T14:15:00Z",
  },
  {
    id: "e-004",
    filePath: "src/models/user_store.py",
    resourceType: "DynamoDB Table",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "applied",
    transformations: [
      { id: "t-006", patternId: "p-dynamo-firestore", patternName: "DynamoDB → Firestore", filePath: "src/models/user_store.py", lineStart: 1, lineEnd: 78, before: "", after: "", confidence: 0.82, status: "applied" },
    ],
    issues: [
      { id: "i-002", entryId: "e-004", filePath: "src/models/user_store.py", line: 45, column: 12, severity: "warning", code: "GSI_MAPPING", message: "DynamoDB Global Secondary Index 'email-index' requires a composite index in Firestore. Performance characteristics differ.", suggestion: "Create a composite index on the 'users' collection for the 'email' field", ruleId: "dynamo-gsi-mapping" },
    ],
    metadata: { tableName: "users", billingMode: "PAY_PER_REQUEST" },
    createdAt: "2026-03-06T10:06:00Z",
    updatedAt: "2026-03-08T14:16:00Z",
  },
  {
    id: "e-005",
    filePath: "infra/main.tf",
    resourceType: "Terraform Module",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "validated",
    transformations: [
      { id: "t-007", patternId: "p-tf-provider", patternName: "AWS Provider → GCP Provider", filePath: "infra/main.tf", lineStart: 1, lineEnd: 12, before: "", after: "", confidence: 0.98, status: "applied" },
      { id: "t-008", patternId: "p-tf-s3-gcs", patternName: "aws_s3_bucket → google_storage_bucket", filePath: "infra/main.tf", lineStart: 14, lineEnd: 35, before: "", after: "", confidence: 0.95, status: "applied" },
      { id: "t-009", patternId: "p-tf-lambda-cf", patternName: "aws_lambda_function → google_cloudfunctions2_function", filePath: "infra/main.tf", lineStart: 37, lineEnd: 72, before: "", after: "", confidence: 0.91, status: "applied" },
    ],
    issues: [],
    metadata: { provider: "hashicorp/aws", version: "~> 5.0" },
    createdAt: "2026-03-06T10:07:00Z",
    updatedAt: "2026-03-08T14:20:00Z",
  },
  {
    id: "e-006",
    filePath: "infra/networking.tf",
    resourceType: "Terraform Module",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "validated",
    transformations: [
      { id: "t-010", patternId: "p-tf-vpc", patternName: "aws_vpc → google_compute_network", filePath: "infra/networking.tf", lineStart: 1, lineEnd: 48, before: "", after: "", confidence: 0.93, status: "applied" },
    ],
    issues: [],
    metadata: {},
    createdAt: "2026-03-06T10:07:00Z",
    updatedAt: "2026-03-08T14:20:00Z",
  },
  {
    id: "e-007",
    filePath: "src/config/secrets.py",
    resourceType: "Secrets Manager",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "planned",
    transformations: [
      { id: "t-011", patternId: "p-secrets", patternName: "Secrets Manager → Secret Manager", filePath: "src/config/secrets.py", lineStart: 1, lineEnd: 22, before: "", after: "", confidence: 0.90, status: "pending" },
    ],
    issues: [],
    metadata: {},
    createdAt: "2026-03-06T10:08:00Z",
    updatedAt: "2026-03-08T14:05:00Z",
  },
  {
    id: "e-008",
    filePath: "src/services/event_bridge.py",
    resourceType: "EventBridge",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "planned",
    transformations: [
      { id: "t-012", patternId: "p-eb-scheduler", patternName: "EventBridge → Cloud Scheduler", filePath: "src/services/event_bridge.py", lineStart: 1, lineEnd: 35, before: "", after: "", confidence: 0.78, status: "pending" },
    ],
    issues: [],
    metadata: {},
    createdAt: "2026-03-06T10:08:00Z",
    updatedAt: "2026-03-08T14:05:00Z",
  },
  {
    id: "e-009",
    filePath: "src/middleware/auth.py",
    resourceType: "Cognito",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "scanned",
    transformations: [],
    issues: [],
    metadata: { userPoolId: "us-east-1_abc123" },
    createdAt: "2026-03-06T10:09:00Z",
    updatedAt: "2026-03-08T13:00:00Z",
  },
  {
    id: "e-010",
    filePath: "src/utils/cache_client.ts",
    resourceType: "ElastiCache",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "scanned",
    transformations: [],
    issues: [],
    metadata: { engine: "redis", nodeType: "cache.t3.micro" },
    createdAt: "2026-03-06T10:09:00Z",
    updatedAt: "2026-03-08T13:00:00Z",
  },
  {
    id: "e-011",
    filePath: "src/api/gateway_config.yaml",
    resourceType: "API Gateway",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "pending",
    transformations: [],
    issues: [],
    metadata: { type: "REST", stage: "prod" },
    createdAt: "2026-03-06T10:10:00Z",
    updatedAt: "2026-03-06T10:10:00Z",
  },
  {
    id: "e-012",
    filePath: "src/handlers/image_processor.py",
    resourceType: "Lambda Function",
    sourceProvider: "aws",
    targetProvider: "gcp",
    status: "validated",
    transformations: [
      { id: "t-013", patternId: "p-lambda-cf", patternName: "Lambda → Cloud Functions", filePath: "src/handlers/image_processor.py", lineStart: 1, lineEnd: 62, before: "", after: "", confidence: 0.89, status: "applied" },
      { id: "t-014", patternId: "p-rekognition-vision", patternName: "Rekognition → Cloud Vision", filePath: "src/handlers/image_processor.py", lineStart: 28, lineEnd: 45, before: "", after: "", confidence: 0.85, status: "applied" },
    ],
    issues: [
      { id: "i-003", entryId: "e-012", filePath: "src/handlers/image_processor.py", line: 38, column: 4, severity: "info", code: "API_PARITY", message: "Rekognition detect_labels returns different confidence format than Cloud Vision. Scores normalized.", ruleId: "rekognition-vision-parity" },
    ],
    metadata: { runtime: "python3.11", memory: 1024, timeout: 120 },
    createdAt: "2026-03-06T10:10:00Z",
    updatedAt: "2026-03-08T14:18:00Z",
  },
];

/* ------------------------------------------------------------------ */
/*  Scan result                                                        */
/* ------------------------------------------------------------------ */

export const SEED_SCAN_RESULT: ScanResult = {
  project_id: "proj-seed",
  root_path: "/srv/payments-service",
  files: [],
  total_files_scanned: 147,
  services_found: [],
  filesScanned: 147,
  resourcesFound: [],
};

/* ------------------------------------------------------------------ */
/*  Plan result                                                        */
/* ------------------------------------------------------------------ */

export const SEED_PLAN_RESULT: PlanResult = {
  id: "plan-b4a3c2d1",
  manifestId: "manifest-001",
  transformations: SEED_ENTRIES.flatMap((e) => e.transformations),
  stepsByPattern: [
    { pattern_id: "s3-client-init", description: "S3 Client Init → GCS", count: 3, step_ids: [], file_paths_sample: [] },
    { pattern_id: "sqs-send", description: "SQS send_message → Pub/Sub", count: 2, step_ids: [], file_paths_sample: [] },
  ],
  diffs: [],
  estimatedChanges: 14,
  riskLevel: "warning",
  timestamp: "2026-03-08T14:00:00Z",
};

/* ------------------------------------------------------------------ */
/*  Diffs                                                              */
/* ------------------------------------------------------------------ */

export const SEED_DIFFS: FileDiff[] = [
  {
    filePath: "src/handlers/payment_processor.py",
    original: `import boto3
import json
from typing import Any

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")

BUCKET_NAME = "payments-data-prod"


def handler(event: dict[str, Any], context: Any) -> dict:
    """Process incoming payment events from SQS."""
    for record in event["Records"]:
        body = json.loads(record["body"])
        payment_id = body["payment_id"]
        amount = body["amount"]
        currency = body["currency"]

        # Store raw event in S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"events/{payment_id}.json",
            Body=json.dumps(body),
            ContentType="application/json",
        )

        # Process payment
        result = process_payment(payment_id, amount, currency)

        # Invoke notification lambda
        lambda_client.invoke(
            FunctionName="notification-sender",
            InvocationType="Event",
            Payload=json.dumps({
                "payment_id": payment_id,
                "status": result["status"],
            }),
        )

    return {"statusCode": 200, "body": "OK"}


def process_payment(payment_id: str, amount: float, currency: str) -> dict:
    # Payment processing logic
    return {"status": "completed", "transaction_id": f"txn_{payment_id}"}`,
    modified: `from google.cloud import storage
from google.cloud import functions_v2
import json
from typing import Any

storage_client = storage.Client()
bucket = storage_client.bucket("payments-data-prod")


def handler(cloud_event: functions_v2.CloudEvent) -> None:
    """Process incoming payment events from Cloud Tasks."""
    data = cloud_event.data
    body = json.loads(data["message"]["data"])
    payment_id = body["payment_id"]
    amount = body["amount"]
    currency = body["currency"]

    # Store raw event in Cloud Storage
    blob = bucket.blob(f"events/{payment_id}.json")
    blob.upload_from_string(
        json.dumps(body),
        content_type="application/json",
    )

    # Process payment
    result = process_payment(payment_id, amount, currency)

    # Publish notification event via Pub/Sub
    from google.cloud import pubsub_v1
    publisher = pubsub_v1.PublisherClient()
    topic = publisher.topic_path("my-project", "notification-events")
    publisher.publish(
        topic,
        json.dumps({
            "payment_id": payment_id,
            "status": result["status"],
        }).encode("utf-8"),
    )


def process_payment(payment_id: str, amount: float, currency: str) -> dict:
    # Payment processing logic
    return {"status": "completed", "transaction_id": f"txn_{payment_id}"}`,
    hunks: [],
    stats: { additions: 22, deletions: 18 },
  },
  {
    filePath: "infra/main.tf",
    original: `terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "payments_data" {
  bucket = "payments-data-\${var.environment}"

  tags = {
    Environment = var.environment
    Service     = "payments"
  }
}

resource "aws_s3_bucket_versioning" "payments_data" {
  bucket = aws_s3_bucket.payments_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_lambda_function" "payment_processor" {
  function_name = "payment-processor"
  runtime       = "python3.11"
  handler       = "payment_processor.handler"
  memory_size   = 512
  timeout       = 30

  s3_bucket = aws_s3_bucket.deploy_bucket.id
  s3_key    = "lambda/payment-processor.zip"

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.payments_data.bucket
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Service = "payments"
  }
}`,
    modified: `terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_storage_bucket" "payments_data" {
  name     = "payments-data-\${var.environment}"
  location = var.gcp_region

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    service     = "payments"
  }
}

resource "google_cloudfunctions2_function" "payment_processor" {
  name     = "payment-processor"
  location = var.gcp_region

  build_config {
    runtime     = "python311"
    entry_point = "handler"
    source {
      storage_source {
        bucket = google_storage_bucket.deploy_bucket.name
        object = "functions/payment-processor.zip"
      }
    }
  }

  service_config {
    available_memory   = "512Mi"
    timeout_seconds    = 30
    max_instance_count = 10

    environment_variables = {
      BUCKET_NAME = google_storage_bucket.payments_data.name
      ENVIRONMENT = var.environment
    }
  }

  labels = {
    service = "payments"
  }
}`,
    hunks: [],
    stats: { additions: 32, deletions: 28 },
  },
  {
    filePath: "src/models/user_store.py",
    original: `import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Optional

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")


def get_user(user_id: str) -> Optional[dict]:
    response = table.get_item(Key={"pk": user_id})
    return response.get("Item")


def query_by_email(email: str) -> list[dict]:
    response = table.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
    )
    return response["Items"]


def create_user(user_id: str, email: str, name: str) -> dict:
    item = {
        "pk": user_id,
        "email": email,
        "name": name,
        "created_at": "2026-03-08T00:00:00Z",
    }
    table.put_item(Item=item)
    return item


def update_user(user_id: str, updates: dict) -> None:
    expr_parts = []
    values = {}
    names = {}
    for i, (k, v) in enumerate(updates.items()):
        expr_parts.append(f"#{k} = :val{i}")
        values[f":val{i}"] = v
        names[f"#{k}"] = k

    table.update_item(
        Key={"pk": user_id},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
    )`,
    modified: `from google.cloud import firestore
from typing import Optional

db = firestore.Client()
users_ref = db.collection("users")


def get_user(user_id: str) -> Optional[dict]:
    doc = users_ref.document(user_id).get()
    return doc.to_dict() if doc.exists else None


def query_by_email(email: str) -> list[dict]:
    docs = users_ref.where("email", "==", email).stream()
    return [doc.to_dict() for doc in docs]


def create_user(user_id: str, email: str, name: str) -> dict:
    data = {
        "email": email,
        "name": name,
        "created_at": "2026-03-08T00:00:00Z",
    }
    users_ref.document(user_id).set(data)
    return {"pk": user_id, **data}


def update_user(user_id: str, updates: dict) -> None:
    users_ref.document(user_id).update(updates)`,
    hunks: [],
    stats: { additions: 14, deletions: 28 },
  },
];

/* ------------------------------------------------------------------ */
/*  Apply result                                                       */
/* ------------------------------------------------------------------ */

export const SEED_APPLY_RESULT: ApplyResult = {
  id: "apply-c3d4e5f6",
  planId: "plan-b2c3d4e5",
  filesModified: 8,
  transformationsApplied: 14,
  errors: [],
  duration: 2400,
  timestamp: "2026-03-08T14:20:12Z",
};

/* ------------------------------------------------------------------ */
/*  Validation result                                                  */
/* ------------------------------------------------------------------ */

export const SEED_VALIDATION: ValidationResult = {
  id: "val-e5f6a7b8",
  manifestId: "manifest-001",
  timestamp: "2026-03-08T14:22:00Z",
  passed: false,
  issues: [
    {
      id: "vi-001",
      entryId: "e-003",
      filePath: "src/services/queue_consumer.py",
      line: 34,
      column: 8,
      severity: "warning",
      code: "DEAD_LETTER_QUEUE",
      message: "SQS dead-letter queue configuration has no direct Cloud Tasks equivalent. Consider using Pub/Sub dead-letter topics.",
      suggestion: "Use google.cloud.pubsub_v1 with dead_letter_policy for retry handling",
      ruleId: "sqs-dlq-mapping",
    },
    {
      id: "vi-002",
      entryId: "e-004",
      filePath: "src/models/user_store.py",
      line: 45,
      column: 12,
      severity: "warning",
      code: "GSI_MAPPING",
      message: "DynamoDB Global Secondary Index 'email-index' requires a composite index in Firestore. Performance characteristics differ.",
      suggestion: "Create a composite index on the 'users' collection for the 'email' field",
      ruleId: "dynamo-gsi-mapping",
    },
    {
      id: "vi-003",
      entryId: "e-012",
      filePath: "src/handlers/image_processor.py",
      line: 38,
      column: 4,
      severity: "info",
      code: "API_PARITY",
      message: "Rekognition detect_labels returns different confidence format than Cloud Vision. Scores normalized.",
      ruleId: "rekognition-vision-parity",
    },
    {
      id: "vi-004",
      entryId: "e-008",
      filePath: "src/services/event_bridge.py",
      line: 12,
      column: 1,
      severity: "error",
      code: "UNSUPPORTED_RULE",
      message: "EventBridge rule with custom event pattern uses content-based filtering not supported by Cloud Scheduler. Requires Eventarc with custom filters.",
      suggestion: "Migrate to Eventarc with Cloud Audit Logs triggers or Pub/Sub message filtering",
      ruleId: "eventbridge-rule-mapping",
    },
    {
      id: "vi-005",
      entryId: "e-001",
      filePath: "src/handlers/payment_processor.py",
      line: 5,
      column: 1,
      severity: "info",
      code: "IMPORT_CLEANUP",
      message: "Residual boto3 import detected in comment on line 5. Not functional but should be removed for clean migration.",
      ruleId: "residual-import-scan",
    },
  ],
  summary: {
    totalIssues: 5,
    errors: 1,
    warnings: 2,
    infos: 2,
    issuesByRule: {
      "sqs-dlq-mapping": 1,
      "dynamo-gsi-mapping": 1,
      "rekognition-vision-parity": 1,
      "eventbridge-rule-mapping": 1,
      "residual-import-scan": 1,
    },
  },
};

/* ------------------------------------------------------------------ */
/*  Patterns (subset for browsing)                                     */
/* ------------------------------------------------------------------ */

export const SEED_PATTERNS: Pattern[] = [
  {
    id: "p-lambda-cf",
    name: "Lambda → Cloud Functions",
    description: "Transform AWS Lambda function handlers to Google Cloud Functions v2 format, including event signature changes and context object mapping.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Compute",
    category: "Compute",
    severity: "warning",
    tags: ["lambda", "cloud-functions", "serverless", "compute"],
    examples: [
      {
        title: "Basic handler migration",
        description: "Convert Lambda event/context handler to CloudEvent-based Cloud Function",
        before: `def handler(event, context):\n    for record in event["Records"]:\n        process(record["body"])\n    return {"statusCode": 200}`,
        after: `def handler(cloud_event):\n    data = cloud_event.data\n    process(data["message"]["data"])\n    # Cloud Functions v2 does not return HTTP responses for event-driven functions`,
      },
    ],
  },
  {
    id: "p-boto3-s3",
    name: "boto3 S3 → google-cloud-storage",
    description: "Convert AWS S3 SDK calls (boto3) to Google Cloud Storage client library equivalents, including bucket operations, object CRUD, and presigned URLs.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Storage",
    category: "Storage",
    severity: "info",
    tags: ["s3", "gcs", "cloud-storage", "boto3", "object-storage"],
    examples: [
      {
        title: "Upload object",
        description: "Convert S3 put_object to GCS blob upload",
        before: `s3.put_object(\n    Bucket="my-bucket",\n    Key="data/file.json",\n    Body=json.dumps(data),\n    ContentType="application/json"\n)`,
        after: `bucket = storage_client.bucket("my-bucket")\nblob = bucket.blob("data/file.json")\nblob.upload_from_string(\n    json.dumps(data),\n    content_type="application/json"\n)`,
      },
    ],
  },
  {
    id: "p-sqs-pubsub",
    name: "SQS → Cloud Tasks / Pub/Sub",
    description: "Transform Amazon SQS queue operations to Google Cloud Tasks or Pub/Sub, depending on the usage pattern (task queue vs. event streaming).",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Messaging",
    category: "Messaging",
    severity: "warning",
    tags: ["sqs", "cloud-tasks", "pubsub", "messaging", "queue"],
    examples: [
      {
        title: "Send message to queue",
        description: "Convert SQS send_message to Pub/Sub publish",
        before: `sqs.send_message(\n    QueueUrl=queue_url,\n    MessageBody=json.dumps(payload),\n    MessageGroupId="order-processing"\n)`,
        after: `publisher = pubsub_v1.PublisherClient()\ntopic = publisher.topic_path(project, "order-processing")\npublisher.publish(\n    topic,\n    json.dumps(payload).encode("utf-8")\n)`,
      },
    ],
  },
  {
    id: "p-dynamo-firestore",
    name: "DynamoDB → Firestore",
    description: "Convert AWS DynamoDB table operations to Google Cloud Firestore, mapping key schemas, queries, and GSIs to Firestore collections and composite indexes.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Database",
    category: "Database",
    severity: "warning",
    tags: ["dynamodb", "firestore", "nosql", "database"],
    examples: [
      {
        title: "Get item by key",
        description: "Convert DynamoDB get_item to Firestore document get",
        before: `response = table.get_item(Key={"pk": user_id})\nitem = response.get("Item")`,
        after: `doc = collection.document(user_id).get()\nitem = doc.to_dict() if doc.exists else None`,
      },
    ],
  },
  {
    id: "p-sns-pubsub",
    name: "SNS → Pub/Sub",
    description: "Transform Amazon SNS topic publish and subscription operations to Google Cloud Pub/Sub equivalents.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Messaging",
    category: "Messaging",
    severity: "info",
    tags: ["sns", "pubsub", "messaging", "notifications"],
    examples: [
      {
        title: "Publish notification",
        description: "Convert SNS publish to Pub/Sub publish",
        before: `sns.publish(\n    TopicArn=topic_arn,\n    Message=json.dumps(payload),\n    Subject="Payment Notification"\n)`,
        after: `publisher.publish(\n    topic_path,\n    json.dumps(payload).encode("utf-8"),\n    subject="Payment Notification"\n)`,
      },
    ],
  },
  {
    id: "p-secrets",
    name: "Secrets Manager → Secret Manager",
    description: "Convert AWS Secrets Manager get/put operations to Google Cloud Secret Manager equivalents.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Security",
    category: "Security",
    severity: "info",
    tags: ["secrets", "secret-manager", "security", "credentials"],
    examples: [
      {
        title: "Retrieve secret value",
        description: "Convert get_secret_value to access_secret_version",
        before: `client = boto3.client("secretsmanager")\nresponse = client.get_secret_value(SecretId="db-password")\nsecret = response["SecretString"]`,
        after: `client = secretmanager.SecretManagerServiceClient()\nname = f"projects/{project}/secrets/db-password/versions/latest"\nresponse = client.access_secret_version(name=name)\nsecret = response.payload.data.decode("utf-8")`,
      },
    ],
  },
  {
    id: "p-tf-s3-gcs",
    name: "aws_s3_bucket → google_storage_bucket",
    description: "Transform Terraform AWS S3 bucket resources to GCP Cloud Storage bucket resources, including versioning, lifecycle, and ACL configurations.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "IaC",
    category: "Infrastructure as Code",
    severity: "info",
    tags: ["terraform", "s3", "gcs", "iac", "storage"],
    examples: [
      {
        title: "Bucket with versioning",
        description: "Convert aws_s3_bucket with versioning to google_storage_bucket",
        before: `resource "aws_s3_bucket" "data" {\n  bucket = "my-data-bucket"\n  tags = { Environment = "prod" }\n}\n\nresource "aws_s3_bucket_versioning" "data" {\n  bucket = aws_s3_bucket.data.id\n  versioning_configuration {\n    status = "Enabled"\n  }\n}`,
        after: `resource "google_storage_bucket" "data" {\n  name     = "my-data-bucket"\n  location = var.gcp_region\n\n  versioning {\n    enabled = true\n  }\n\n  labels = {\n    environment = "prod"\n  }\n}`,
      },
    ],
  },
  {
    id: "p-tf-vpc",
    name: "aws_vpc → google_compute_network",
    description: "Transform Terraform AWS VPC and subnet resources to GCP VPC network and subnetwork equivalents.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "IaC",
    category: "Infrastructure as Code",
    severity: "warning",
    tags: ["terraform", "vpc", "networking", "iac"],
    examples: [
      {
        title: "VPC with subnets",
        description: "Convert AWS VPC to GCP VPC network",
        before: `resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n  tags = { Name = "main-vpc" }\n}`,
        after: `resource "google_compute_network" "main" {\n  name                    = "main-vpc"\n  auto_create_subnetworks = false\n}`,
      },
    ],
  },
  {
    id: "p-cognito-identity",
    name: "Cognito → Identity Platform",
    description: "Convert AWS Cognito User Pool authentication flows to Google Cloud Identity Platform (Firebase Auth) equivalents.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Auth",
    category: "Security",
    severity: "error",
    tags: ["cognito", "identity-platform", "auth", "firebase"],
    examples: [
      {
        title: "User authentication",
        description: "Convert Cognito sign-in to Identity Platform",
        before: `response = cognito.initiate_auth(\n    ClientId=client_id,\n    AuthFlow="USER_PASSWORD_AUTH",\n    AuthParameters={\n        "USERNAME": username,\n        "PASSWORD": password\n    }\n)`,
        after: `from firebase_admin import auth\nuser = auth.get_user_by_email(username)\ncustom_token = auth.create_custom_token(user.uid)`,
      },
    ],
  },
  {
    id: "p-eb-scheduler",
    name: "EventBridge → Cloud Scheduler",
    description: "Convert AWS EventBridge scheduled rules and event patterns to Google Cloud Scheduler jobs with Pub/Sub or HTTP targets.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Integration",
    category: "Integration",
    severity: "warning",
    tags: ["eventbridge", "cloud-scheduler", "cron", "events"],
    examples: [
      {
        title: "Scheduled rule",
        description: "Convert EventBridge cron rule to Cloud Scheduler",
        before: `events.put_rule(\n    Name="nightly-cleanup",\n    ScheduleExpression="cron(0 2 * * ? *)",\n    State="ENABLED"\n)`,
        after: `from google.cloud import scheduler_v1\nclient = scheduler_v1.CloudSchedulerClient()\njob = scheduler_v1.Job(\n    name="nightly-cleanup",\n    schedule="0 2 * * *",\n    pubsub_target={...}\n)\nclient.create_job(parent=parent, job=job)`,
      },
    ],
  },
  {
    id: "p-rekognition-vision",
    name: "Rekognition → Cloud Vision",
    description: "Convert AWS Rekognition image analysis calls to Google Cloud Vision API equivalents, including label detection, face detection, and text extraction.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "AI/ML",
    category: "AI & Machine Learning",
    severity: "info",
    tags: ["rekognition", "cloud-vision", "ai", "image-analysis"],
    examples: [
      {
        title: "Label detection",
        description: "Convert Rekognition detect_labels to Cloud Vision",
        before: `response = rekognition.detect_labels(\n    Image={"S3Object": {"Bucket": bucket, "Name": key}},\n    MaxLabels=10\n)\nlabels = [l["Name"] for l in response["Labels"]]`,
        after: `from google.cloud import vision\nclient = vision.ImageAnnotatorClient()\nimage = vision.Image(source=vision.ImageSource(gcs_image_uri=uri))\nresponse = client.label_detection(image=image, max_results=10)\nlabels = [l.description for l in response.label_annotations]`,
      },
    ],
  },
  {
    id: "p-elasticache-memorystore",
    name: "ElastiCache → Memorystore",
    description: "Convert AWS ElastiCache Redis/Memcached connection configurations to Google Cloud Memorystore equivalents.",
    sourceProvider: "aws",
    targetProvider: "gcp",
    resourceType: "Cache",
    category: "Database",
    severity: "info",
    tags: ["elasticache", "memorystore", "redis", "cache"],
    examples: [
      {
        title: "Redis connection",
        description: "Update Redis connection string for Memorystore",
        before: `import redis\nr = redis.Redis(\n    host=os.environ["ELASTICACHE_ENDPOINT"],\n    port=6379,\n    ssl=True\n)`,
        after: `import redis\nr = redis.Redis(\n    host=os.environ["MEMORYSTORE_HOST"],\n    port=6379\n    # Memorystore uses VPC peering, no SSL needed for internal traffic\n)`,
      },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Fix data for inline fix overlay                                    */
/* ------------------------------------------------------------------ */

export interface FixData {
  original: string;
  fixed: string;
  language: string;
}

export const SEED_FIX_DATA: Record<string, FixData> = {
  "vi-001": {
    language: "python",
    original: `import boto3
import json

sqs = boto3.client("sqs")

def consume_messages(queue_url: str):
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
        )

        for msg in response.get("Messages", []):
            try:
                body = json.loads(msg["Body"])
                process_event(body)
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )
            except Exception:
                # Message returns to queue after visibility timeout
                # DLQ receives after maxReceiveCount
                pass


def setup_dlq():
    dlq = sqs.create_queue(QueueName="payments-dlq")
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=dlq["QueueUrl"],
        AttributeNames=["QueueArn"],
    )["Attributes"]["QueueArn"]

    sqs.set_queue_attributes(
        QueueUrl="payments-queue",
        Attributes={
            "RedrivePolicy": json.dumps({
                "deadLetterTargetArn": dlq_arn,
                "maxReceiveCount": 3,
            })
        },
    )`,
    fixed: `from google.cloud import pubsub_v1
import json

subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

def consume_messages(subscription_path: str):
    def callback(message):
        try:
            body = json.loads(message.data.decode("utf-8"))
            process_event(body)
            message.ack()
        except Exception:
            # Message will be redelivered after ack deadline
            # Dead-letter topic receives after max delivery attempts
            message.nack()

    streaming_pull = subscriber.subscribe(subscription_path, callback=callback)
    streaming_pull.result()


def setup_dlq(project: str, topic: str, subscription: str):
    # Create dead-letter topic
    dlq_topic = publisher.topic_path(project, f"{topic}-dlq")
    publisher.create_topic(request={"name": dlq_topic})

    # Create subscription for DLQ
    dlq_sub = subscriber.subscription_path(project, f"{subscription}-dlq")
    subscriber.create_subscription(
        request={"name": dlq_sub, "topic": dlq_topic}
    )

    # Update main subscription with dead-letter policy
    sub_path = subscriber.subscription_path(project, subscription)
    subscriber.update_subscription(
        request={
            "subscription": {
                "name": sub_path,
                "dead_letter_policy": {
                    "dead_letter_topic": dlq_topic,
                    "max_delivery_attempts": 3,
                },
            },
            "update_mask": {"paths": ["dead_letter_policy"]},
        }
    )`,
  },
  "vi-002": {
    language: "python",
    original: `import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")


def query_users_by_email(email: str) -> list[dict]:
    """Query users using the email-index GSI."""
    response = table.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email),
    )
    return response["Items"]


def query_users_by_status(status: str, created_after: str) -> list[dict]:
    """Query users by status with a sort key condition."""
    response = table.query(
        IndexName="status-created-index",
        KeyConditionExpression=(
            Key("status").eq(status) &
            Key("created_at").gt(created_after)
        ),
        FilterExpression=Attr("active").eq(True),
    )
    return response["Items"]`,
    fixed: `from google.cloud import firestore

db = firestore.Client()
users_ref = db.collection("users")

# NOTE: Ensure composite indexes are created in Firestore:
#   - Collection: users | Fields: email ASC
#   - Collection: users | Fields: status ASC, created_at ASC


def query_users_by_email(email: str) -> list[dict]:
    """Query users by email field (replaces email-index GSI)."""
    docs = users_ref.where("email", "==", email).stream()
    return [doc.to_dict() | {"id": doc.id} for doc in docs]


def query_users_by_status(status: str, created_after: str) -> list[dict]:
    """Query users by status with ordering (replaces status-created-index GSI)."""
    query = (
        users_ref
        .where("status", "==", status)
        .where("created_at", ">", created_after)
        .where("active", "==", True)
        .order_by("created_at")
    )
    docs = query.stream()
    return [doc.to_dict() | {"id": doc.id} for doc in docs]`,
  },
  "vi-004": {
    language: "python",
    original: `import boto3
import json

events = boto3.client("events")


def create_payment_rule():
    """EventBridge rule with content-based filtering."""
    events.put_rule(
        Name="high-value-payments",
        EventPattern=json.dumps({
            "source": ["payments.service"],
            "detail-type": ["PaymentProcessed"],
            "detail": {
                "amount": [{"numeric": [">=", 10000]}],
                "currency": ["USD", "EUR"],
                "status": [{"anything-but": "failed"}],
            },
        }),
        State="ENABLED",
    )

    events.put_targets(
        Rule="high-value-payments",
        Targets=[
            {
                "Id": "fraud-check",
                "Arn": "arn:aws:lambda:us-east-1:123456:function:fraud-detector",
                "InputTransformer": {
                    "InputPathsMap": {
                        "payment_id": "$.detail.payment_id",
                        "amount": "$.detail.amount",
                    },
                    "InputTemplate": '{"id": <payment_id>, "amount": <amount>}',
                },
            }
        ],
    )`,
    fixed: `from google.cloud import pubsub_v1
from google.cloud import functions_v2
import json

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()


def create_payment_rule(project: str):
    """Eventarc-based filtering via Pub/Sub message filtering."""
    # Create topic for payment events
    topic_path = publisher.topic_path(project, "high-value-payments")
    publisher.create_topic(request={"name": topic_path})

    # Create filtered subscription (replaces EventBridge content filtering)
    sub_path = subscriber.subscription_path(
        project, "high-value-payments-fraud-check"
    )
    subscriber.create_subscription(
        request={
            "name": sub_path,
            "topic": topic_path,
            "filter": 'attributes.source = "payments.service" AND '
                      'attributes.detail_type = "PaymentProcessed"',
            "push_config": {
                "push_endpoint": (
                    f"https://{project}.cloudfunctions.net/fraud-detector"
                ),
            },
        }
    )

    # NOTE: Pub/Sub filtering only supports attribute-based filtering.
    # For numeric/content-based filtering (amount >= 10000), add
    # validation logic in the Cloud Function itself:
    #
    # def fraud_detector(cloud_event):
    #     data = json.loads(cloud_event.data["message"]["data"])
    #     if data["amount"] < 10000:
    #         return  # skip low-value
    #     if data["currency"] not in ("USD", "EUR"):
    #         return  # skip other currencies
    #     if data["status"] == "failed":
    #         return  # skip failed
    #     run_fraud_check(data)`,
  },
};
