# CloudShift Pattern Catalogue

**134 migration patterns** across 4 languages and 2 source cloud providers.

---

## AWS to GCP (96 patterns)

### Compute

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| EC2 Instance CloudFormation to Compute Engine (Terraform) | ec2 | compute-engine | CloudFormation | 72% |
| Lambda CloudFormation to Cloud Functions (Terraform) | lambda | cloud-functions | CloudFormation | 75% |
| AWS EC2 Instance to GCP Compute Instance (Terraform) | ec2 | compute-engine | Terraform | 80% |
| AWS ECS Service to GCP Cloud Run (Terraform) | ecs | cloud-run | Terraform | 75% |
| AWS EKS Cluster to GCP GKE Cluster (Terraform) | eks | gke | Terraform | 78% |
| AWS Lambda Function to Cloud Function (Terraform) | lambda | cloud-functions | Terraform | 85% |
| EC2 Instance to Compute Engine (Terraform) | ec2 | compute-engine | Terraform | 75% |
| ECS Fargate Service to Cloud Run (Terraform) | ecs | cloud-run | Terraform | 72% |
| EKS Cluster to GKE (Terraform) | eks | gke | Terraform | 70% |
| AWS Lambda Handler to Cloud Functions (Python) | lambda | cloud-functions | Python | 80% |
| Lambda handler to Cloud Function entry point (Python) | lambda | cloud-functions | Python | 82% |
| Lambda Handler to Cloud Function Handler (TypeScript) | lambda | cloud-functions | TypeScript | 80% |

### Storage

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| S3 Bucket CloudFormation to GCS Bucket (Terraform) | s3 | cloud-storage | CloudFormation | 70% |
| S3 Bucket to GCS Bucket (Terraform) | s3 | cloud-storage | Terraform | 85% |
| S3 Client Init to GCS Client (Python) | s3 | cloud-storage | Python | 92% |
| S3 delete_object to GCS blob.delete (Python) | s3 | cloud-storage | Python | 90% |
| S3 generate_presigned_url to GCS generate_signed_url (Python) | s3 | cloud-storage | Python | 80% |
| S3 get_object to GCS download_as_bytes (Python) | s3 | cloud-storage | Python | 90% |
| S3 list_objects to GCS list_blobs (Python) | s3 | cloud-storage | Python | 88% |
| S3 put_object to GCS upload_from_string (Python) | s3 | cloud-storage | Python | 90% |
| SSM Parameter Store to Secret Manager (Python) | ssm | secret-manager | Python | 75% |
| S3 Client Init to GCS Client (TypeScript) | s3 | cloud-storage | TypeScript | 92% |
| S3 DeleteObject to GCS File Delete (TypeScript) | s3 | cloud-storage | TypeScript | 85% |
| S3 GetObjectCommand to GCS file.download (TypeScript) | s3 | cloud-storage | TypeScript | 90% |
| S3 ListObjectsV2 to GCS getFiles (TypeScript) | s3 | cloud-storage | TypeScript | 85% |
| S3 PutObjectCommand to GCS file.save (TypeScript) | s3 | cloud-storage | TypeScript | 90% |

### Database

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| DynamoDB CloudFormation to Firestore (Terraform) | dynamodb | firestore | CloudFormation | 72% |
| RDS CloudFormation to Cloud SQL (Terraform) | rds | cloud-sql | CloudFormation | 70% |
| AWS RDS Aurora to GCP Cloud SQL with HA (Terraform) | rds-aurora | cloud-sql | Terraform | 72% |
| DynamoDB Table to Firestore Database (Terraform) | dynamodb | firestore | Terraform | 68% |
| ElastiCache Redis to Memorystore (Terraform) | elasticache | memorystore | Terraform | 80% |
| RDS Instance to Cloud SQL (Terraform) | rds | cloud-sql | Terraform | 78% |
| DynamoDB Client Init to Firestore Client (Python) | dynamodb | firestore | Python | 80% |
| DynamoDB batch_writer to Firestore batch (Python) | dynamodb | firestore | Python | 78% |
| DynamoDB delete_item to Firestore delete (Python) | dynamodb | firestore | Python | 88% |
| DynamoDB get_item to Firestore document.get (Python) | dynamodb | firestore | Python | 85% |
| DynamoDB put_item to Firestore document.set (Python) | dynamodb | firestore | Python | 82% |
| DynamoDB query to Firestore where().stream (Python) | dynamodb | firestore | Python | 72% |
| DynamoDB scan to Firestore stream (Python) | dynamodb | firestore | Python | 75% |
| RDS client to Cloud SQL connector (Python) | rds | cloud-sql | Python | 70% |
| DynamoDB Client Init to Firestore (TypeScript) | dynamodb | firestore | TypeScript | 82% |
| DynamoDB DeleteItem to Firestore Document Delete (TypeScript) | dynamodb | firestore | TypeScript | 85% |
| DynamoDB GetItem to Firestore Document Get (TypeScript) | dynamodb | firestore | TypeScript | 80% |
| DynamoDB PutItem to Firestore Document Set (TypeScript) | dynamodb | firestore | TypeScript | 80% |
| DynamoDB Query to Firestore Collection Query (TypeScript) | dynamodb | firestore | TypeScript | 75% |

### Messaging

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| SNS CloudFormation to Pub/Sub (Terraform) | sns | pubsub | CloudFormation | 78% |
| SQS CloudFormation to Pub/Sub (Terraform) | sqs | pubsub | CloudFormation | 72% |
| EventBridge to Eventarc (Terraform) | eventbridge | eventarc | Terraform | 65% |
| SNS Topic Subscription to Pub/Sub Subscription (Terraform) | sns | pubsub | Terraform | 82% |
| SNS Topic to Pub/Sub Topic (Terraform) | sns | pubsub | Terraform | 82% |
| SQS Queue to Pub/Sub Topic + Subscription (Terraform) | sqs | pubsub | Terraform | 82% |
| SNS client init to Pub/Sub PublisherClient (Python) | sns | pubsub | Python | 90% |
| SNS publish to Pub/Sub publish (Python) | sns | pubsub | Python | 88% |
| SQS Client Init to Pub/Sub Client (Python) | sqs | pubsub | Python | 82% |
| SQS receive_message to Pub/Sub pull (Python) | sqs | pubsub | Python | 80% |
| SQS send_message to Pub/Sub publish (Python) | sqs | pubsub | Python | 85% |
| SNS Publish to PubSub publishMessage (TypeScript) | sns | pubsub | TypeScript | 85% |
| SQS Client Init to PubSub Client Init (TypeScript) | sqs | pubsub | TypeScript | 85% |
| SQS ReceiveMessage to PubSub Subscription Pull (TypeScript) | sqs | pubsub | TypeScript | 75% |
| SQS SendMessage to PubSub publishMessage (TypeScript) | sqs | pubsub | TypeScript | 85% |

### Secrets & Encryption

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| KMS Key CloudFormation to Cloud KMS (Terraform) | kms | cloud-kms | CloudFormation | 72% |
| Secrets Manager CloudFormation to Secret Manager (Terraform) | secretsmanager | secret-manager | CloudFormation | 78% |
| AWS KMS Key to GCP Cloud KMS (Terraform) | kms | cloud-kms | Terraform | 78% |
| AWS Secrets Manager to GCP Secret Manager (Terraform) | secretsmanager | secret-manager | Terraform | 88% |
| AWS Secrets Manager Client to GCP Secret Manager (Python) | secretsmanager | secret-manager | Python | 90% |
| AWS get_secret_value to GCP access_secret_version (Python) | secretsmanager | secret-manager | Python | 88% |
| Secrets Manager create_secret to Secret Manager (Python) | secretsmanager | secret-manager | Python | 82% |
| Secrets Manager update_secret to Secret Manager (Python) | secretsmanager | secret-manager | Python | 82% |
| SecretsManager Client Init to GCP Secret Manager (TypeScript) | secrets-manager | secret-manager | TypeScript | 90% |
| SecretsManager GetSecretValue to GCP accessSecretVersion (TypeScript) | secrets-manager | secret-manager | TypeScript | 85% |

### IAM & Identity

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| IAM Role CloudFormation to Service Account (Terraform) | iam | iam | CloudFormation | 68% |
| AWS IAM Policy to GCP IAM Binding (Terraform) | iam | iam | Terraform | 65% |
| AWS IAM Role to GCP IAM Member (Terraform) | iam | iam | Terraform | 72% |
| AWS Credential Environment Variables to GCP (Python) | iam | iam | Python | 78% |
| STS assume_role to GCP service account impersonation (Python) | sts | iam | Python | 72% |
| AWS Environment Variables to GCP Environment Variables (TypeScript) | iam | iam | TypeScript | 85% |

### Monitoring & Logging

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| AWS CloudWatch Dashboard to GCP Monitoring Dashboard (Terraform) | cloudwatch | cloud-monitoring | Terraform | 70% |
| AWS CloudWatch Log Group to GCP Logging Bucket (Terraform) | cloudwatch-logs | cloud-logging | Terraform | 75% |
| CloudWatch Logs to Cloud Logging (Python) | logs | cloud-logging | Python | 78% |
| CloudWatch put_metric_data to Cloud Monitoring (Python) | cloudwatch | cloud-monitoring | Python | 75% |

### Networking

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| VPC CloudFormation to Compute Network (Terraform) | vpc | compute-network | CloudFormation | 70% |
| AWS ALB to GCP HTTP(S) Load Balancer (Terraform) | alb | compute-load-balancer | Terraform | 72% |
| AWS Security Group to GCP Firewall Rule (Terraform) | security-group | compute-firewall | Terraform | 78% |
| AWS VPC to GCP VPC Network (Terraform) | vpc | compute-network | Terraform | 82% |

### Infrastructure / Other

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| AWS API Gateway to GCP API Gateway (Terraform) | api-gateway | api-gateway | Terraform | 60% |
| AWS Cognito to GCP Identity Platform (Terraform) | cognito | identity-platform | Terraform | 65% |
| AWS ECR to GCP Artifact Registry (Terraform) | ecr | artifact-registry | Terraform | 88% |
| AWS Provider to Google Provider (Terraform) | terraform | terraform | Terraform | 92% |
| AWS SES to GCP Email / Third-Party (Terraform) | ses | smtp-third-party | Terraform | 55% |
| AWS SSM Parameter to GCP Secret Manager (Terraform) | ssm | secret-manager | Terraform | 82% |
| AWS WAFv2 to GCP Cloud Armor (Terraform) | waf | cloud-armor | Terraform | 70% |
| CloudFront Distribution to Cloud CDN (Terraform) | cloudfront | cloud-cdn | Terraform | 65% |
| CloudWatch to Cloud Monitoring (Terraform) | cloudwatch | cloud-monitoring | Terraform | 70% |
| Kinesis Data Stream to Dataflow (Terraform) | kinesis | dataflow | Terraform | 65% |
| Route53 to Cloud DNS (Terraform) | route53 | cloud-dns | Terraform | 82% |
| Step Functions to Cloud Workflows (Terraform) | step-functions | workflows | Terraform | 58% |

---

## Azure to GCP (37 patterns)

### Compute

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| AKS Cluster to GKE (Terraform) | aks | gke | Terraform | 72% |
| Azure Function App to Cloud Functions (Terraform) | functions | cloud-functions | Terraform | 78% |
| Azure Virtual Machine to Compute Engine (Terraform) | virtual-machines | compute-engine | Terraform | 75% |
| Azure Functions to Cloud Functions (Python) | azure-functions | cloud-functions | Python | 78% |

### Storage

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure Storage Account to GCS Bucket (Terraform) | blob-storage | cloud-storage | Terraform | 80% |
| Azure Blob Client to GCS Client (Python) | blob-storage | cloud-storage | Python | 90% |
| Azure Blob SAS Token to GCS Signed URL (Python) | blob-storage | cloud-storage | Python | 75% |
| Azure Blob delete_blob to GCS blob.delete (Python) | blob-storage | cloud-storage | Python | 88% |
| Azure Blob download_blob to GCS download_as_bytes (Python) | blob-storage | cloud-storage | Python | 88% |
| Azure Blob list_blobs to GCS bucket.list_blobs (Python) | blob-storage | cloud-storage | Python | 85% |
| Azure Blob upload_blob to GCS upload_from_string (Python) | blob-storage | cloud-storage | Python | 88% |

### Database

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure SQL Server to Cloud SQL (Terraform) | azure-sql | cloud-sql | Terraform | 72% |
| CosmosDB Account to Firestore Database (Terraform) | cosmosdb | firestore | Terraform | 65% |
| Azure SQL pyodbc to Cloud SQL Connector (Python) | sql | cloud-sql | Python | 68% |
| CosmosDB Client to Firestore Client (Python) | cosmosdb | firestore | Python | 72% |
| CosmosDB create_item to Firestore document.set (Python) | cosmosdb | firestore | Python | 85% |
| CosmosDB delete_item to Firestore document.delete (Python) | cosmosdb | firestore | Python | 88% |
| CosmosDB query_items to Firestore where.stream (Python) | cosmosdb | firestore | Python | 78% |
| CosmosDB read_item to Firestore document.get (Python) | cosmosdb | firestore | Python | 85% |

### Messaging

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure Event Hub Namespace to Pub/Sub Topic (Terraform) | event-hubs | pubsub | Terraform | 75% |
| Azure Event Hub to Pub/Sub (Terraform) | event-hubs | pubsub | Terraform | 78% |
| Azure Service Bus Queue to Pub/Sub (Terraform) | service-bus | pubsub | Terraform | 78% |
| Azure Service Bus Topic to Pub/Sub (Terraform) | service-bus | pubsub | Terraform | 80% |
| Azure Service Bus to Pub/Sub (Terraform) | service-bus | pubsub | Terraform | 80% |
| Azure Event Hub to Pub/Sub Client Init (Python) | event-hub | pubsub | Python | 75% |
| Azure Service Bus receive_messages to Pub/Sub pull (Python) | service-bus | pubsub | Python | 78% |
| Azure Service Bus send_messages to Pub/Sub publish (Python) | service-bus | pubsub | Python | 82% |
| Azure Service Bus to Pub/Sub (Python) | service-bus | pubsub | Python | 78% |

### Secrets & Encryption

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure Key Vault to GCP Secret Manager (Terraform) | key-vault | secret-manager | Terraform | 78% |

### IAM & Identity

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure Managed Identity to GCP Service Account (Terraform) | managed-identity | iam | Terraform | 80% |
| Azure DefaultAzureCredential to GCP google.auth (Python) | azure-identity | iam | Python | 82% |
| Azure Key Vault Secret Operations to GCP Secret Manager (Python) | key-vault | secret-manager | Python | 80% |
| Azure Key Vault to GCP Secret Manager (Python) | key-vault | secret-manager | Python | 85% |

### Monitoring & Logging

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure Application Insights to Cloud Monitoring (Python) | monitor | cloud-monitoring | Python | 65% |

### Networking

| Pattern | Source | Target | Language | Confidence |
|---------|--------|--------|----------|------------|
| Azure Application Gateway to GCP HTTP(S) Load Balancer (Terraform) | application-gateway | cloud-load-balancing | Terraform | 68% |
| Azure NSG to GCP Firewall Rules (Terraform) | network-security-group | compute-firewall | Terraform | 75% |
| Azure Virtual Network to GCP VPC (Terraform) | virtual-network | vpc | Terraform | 80% |

---

## Coverage by Language

| Language | AWS Patterns | Azure Patterns | Total |
|----------|-------------|----------------|-------|
| Python | 27 | 19 | 46 |
| TypeScript | 17 | 0 | 17 |
| Terraform (HCL) | 41 | 17 | 58 |
| CloudFormation | 11 | 0 | 11 |
| **Total** | **96** | **37** (*)| **134** (*)  |

(*) One pattern file (`lambda_to_cloud_functions.yaml`) contains a multi-document YAML; the Rust loader counts it as 2, bringing the runtime total to 134.

## Coverage by Service Category

| Category | AWS Patterns | Azure Patterns |
|----------|-------------|----------------|
| Compute | 12 | 4 |
| Storage | 14 | 7 |
| Database | 19 | 8 |
| Messaging | 15 | 9 |
| Secrets & Encryption | 10 | 1 |
| IAM & Identity | 6 | 4 |
| Monitoring & Logging | 4 | 1 |
| Networking | 4 | 3 |
| Infrastructure / Other | 12 | 0 |
