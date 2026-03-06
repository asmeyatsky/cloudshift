use std::collections::HashMap;

use crate::parser::{AstNode, NodeType};

use super::{CloudProvider, ServiceDetection};

pub fn detect(node: &AstNode) -> Option<ServiceDetection> {
    match &node.node_type {
        NodeType::Import => detect_import(node),
        NodeType::ClientInit => detect_client_init(node),
        NodeType::ResourceBlock => detect_resource_block(node),
        NodeType::StringLiteral => detect_arn(node),
        NodeType::EnvVar => detect_env_var(node),
        NodeType::MethodCall => detect_method_call(node),
        _ => None,
    }
}

fn detect_import(node: &AstNode) -> Option<ServiceDetection> {
    let name = &node.name;
    let text = &node.text;

    // Python boto3
    if name == "boto3" || name == "botocore" || text.contains("boto3") || text.contains("botocore")
    {
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service: "sdk".to_string(),
            construct_type: "import".to_string(),
            confidence: 0.95,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    // TypeScript @aws-sdk
    if name.contains("@aws-sdk") || text.contains("@aws-sdk") {
        let service = extract_aws_sdk_service(text);
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service,
            construct_type: "import".to_string(),
            confidence: 0.95,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    // AWS CDK
    if text.contains("aws-cdk") || text.contains("@aws-cdk") {
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service: "cdk".to_string(),
            construct_type: "import".to_string(),
            confidence: 0.90,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    None
}

fn detect_client_init(node: &AstNode) -> Option<ServiceDetection> {
    let text = &node.text;
    let name = &node.name;

    // boto3.client('service') or boto3.resource('service')
    if name.contains("boto3.client") || name.contains("boto3.resource") {
        let service = extract_boto3_service(text);
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service,
            construct_type: "client_init".to_string(),
            confidence: 0.95,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    // TypeScript AWS SDK client constructors
    let ts_clients = [
        ("S3Client", "s3"),
        ("DynamoDBClient", "dynamodb"),
        ("LambdaClient", "lambda"),
        ("SQSClient", "sqs"),
        ("SNSClient", "sns"),
        ("EC2Client", "ec2"),
        ("IAMClient", "iam"),
        ("SecretsManagerClient", "secretsmanager"),
        ("KMSClient", "kms"),
        ("CloudWatchClient", "cloudwatch"),
        ("ECSClient", "ecs"),
        ("EKSClient", "eks"),
        ("RDSClient", "rds"),
        ("ElastiCacheClient", "elasticache"),
        ("Route53Client", "route53"),
        ("CloudFrontClient", "cloudfront"),
        ("APIGatewayClient", "apigateway"),
        ("StepFunctionsClient", "stepfunctions"),
        ("EventBridgeClient", "eventbridge"),
        ("KinesisClient", "kinesis"),
    ];

    for (client_name, service) in &ts_clients {
        if name.contains(client_name) || text.contains(client_name) {
            return Some(ServiceDetection {
                provider: CloudProvider::Aws,
                service: service.to_string(),
                construct_type: "client_init".to_string(),
                confidence: 0.95,
                node_name: node.name.clone(),
                start_line: node.start_line,
                end_line: node.end_line,
                metadata: HashMap::new(),
            });
        }
    }

    None
}

fn detect_resource_block(node: &AstNode) -> Option<ServiceDetection> {
    let resource_type = node
        .metadata
        .get("resource_type")
        .map(|s| s.as_str())
        .unwrap_or("");

    // Terraform aws_ resources
    if resource_type.starts_with("aws_") {
        let service = extract_terraform_service(resource_type);
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service,
            construct_type: "resource_block".to_string(),
            confidence: 0.98,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: node.metadata.clone(),
        });
    }

    // CloudFormation AWS:: types
    if resource_type.starts_with("AWS::") {
        let service = extract_cfn_service(resource_type);
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service,
            construct_type: "resource_block".to_string(),
            confidence: 0.98,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: node.metadata.clone(),
        });
    }

    None
}

fn detect_arn(node: &AstNode) -> Option<ServiceDetection> {
    if node.text.contains("arn:aws:") {
        // Parse ARN: arn:aws:service:region:account:resource
        let parts: Vec<&str> = node.text.split(':').collect();
        let service = parts.get(2).unwrap_or(&"unknown").to_string();
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service,
            construct_type: "arn_reference".to_string(),
            confidence: 0.90,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    if node.text.contains("amazonaws.com") {
        return Some(ServiceDetection {
            provider: CloudProvider::Aws,
            service: "endpoint".to_string(),
            construct_type: "endpoint_reference".to_string(),
            confidence: 0.85,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    None
}

fn detect_env_var(node: &AstNode) -> Option<ServiceDetection> {
    let aws_env_patterns = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_PROFILE",
    ];

    for pattern in &aws_env_patterns {
        if node.text.contains(pattern) {
            return Some(ServiceDetection {
                provider: CloudProvider::Aws,
                service: "iam".to_string(),
                construct_type: "env_var".to_string(),
                confidence: 0.90,
                node_name: node.name.clone(),
                start_line: node.start_line,
                end_line: node.end_line,
                metadata: HashMap::new(),
            });
        }
    }

    None
}

fn detect_method_call(node: &AstNode) -> Option<ServiceDetection> {
    // Detect common boto3 method patterns like s3.put_object, dynamodb.put_item
    let aws_methods = [
        ("put_object", "s3"),
        ("get_object", "s3"),
        ("list_objects", "s3"),
        ("delete_object", "s3"),
        ("upload_file", "s3"),
        ("download_file", "s3"),
        ("put_item", "dynamodb"),
        ("get_item", "dynamodb"),
        ("query", "dynamodb"),
        ("scan", "dynamodb"),
        ("invoke", "lambda"),
        ("send_message", "sqs"),
        ("receive_message", "sqs"),
        ("publish", "sns"),
    ];

    for (method, service) in &aws_methods {
        if node.name.ends_with(method) || node.text.contains(method) {
            return Some(ServiceDetection {
                provider: CloudProvider::Aws,
                service: service.to_string(),
                construct_type: "method_call".to_string(),
                confidence: 0.70,
                node_name: node.name.clone(),
                start_line: node.start_line,
                end_line: node.end_line,
                metadata: HashMap::new(),
            });
        }
    }

    None
}

fn extract_boto3_service(text: &str) -> String {
    // Extract service name from boto3.client('s3') or boto3.resource('dynamodb')
    if let Some(start) = text.find('\'').or_else(|| text.find('"')) {
        let rest = &text[start + 1..];
        if let Some(end) = rest.find('\'').or_else(|| rest.find('"')) {
            return rest[..end].to_string();
        }
    }
    "unknown".to_string()
}

fn extract_aws_sdk_service(text: &str) -> String {
    // Extract from @aws-sdk/client-s3
    if let Some(idx) = text.find("client-") {
        let rest = &text[idx + 7..];
        let end = rest.find('"').or_else(|| rest.find('\'')).unwrap_or(rest.len());
        return rest[..end].to_string();
    }
    "sdk".to_string()
}

fn extract_terraform_service(resource_type: &str) -> String {
    // aws_s3_bucket -> s3, aws_dynamodb_table -> dynamodb
    let without_prefix = resource_type.strip_prefix("aws_").unwrap_or(resource_type);
    let service_map = [
        ("s3_", "s3"),
        ("dynamodb_", "dynamodb"),
        ("lambda_", "lambda"),
        ("sqs_", "sqs"),
        ("sns_", "sns"),
        ("ec2_", "ec2"),
        ("iam_", "iam"),
        ("secretsmanager_", "secretsmanager"),
        ("kms_", "kms"),
        ("cloudwatch_", "cloudwatch"),
        ("ecs_", "ecs"),
        ("eks_", "eks"),
        ("rds_", "rds"),
        ("elasticache_", "elasticache"),
        ("route53_", "route53"),
        ("cloudfront_", "cloudfront"),
        ("api_gateway", "apigateway"),
        ("sfn_", "stepfunctions"),
        ("cloudformation_", "cloudformation"),
        ("kinesis_", "kinesis"),
        ("db_", "rds"),
        ("instance", "ec2"),
        ("vpc", "vpc"),
        ("subnet", "vpc"),
        ("security_group", "vpc"),
        ("lb_", "elb"),
        ("alb_", "elb"),
    ];

    for (prefix, service) in &service_map {
        if without_prefix.starts_with(prefix) {
            return service.to_string();
        }
    }

    // Fallback: use first segment
    without_prefix
        .split('_')
        .next()
        .unwrap_or("unknown")
        .to_string()
}

fn extract_cfn_service(resource_type: &str) -> String {
    // AWS::S3::Bucket -> s3, AWS::DynamoDB::Table -> dynamodb
    let parts: Vec<&str> = resource_type.split("::").collect();
    parts
        .get(1)
        .unwrap_or(&"unknown")
        .to_lowercase()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_boto3_import() {
        let node = AstNode {
            node_type: NodeType::Import,
            name: "boto3".into(),
            text: "import boto3".into(),
            start_line: 1,
            end_line: 1,
            start_col: 0,
            end_col: 12,
            children: vec![],
            metadata: HashMap::new(),
        };
        let detection = detect(&node).unwrap();
        assert_eq!(detection.provider, CloudProvider::Aws);
        assert_eq!(detection.service, "sdk");
    }

    #[test]
    fn test_detect_s3_client_init() {
        let node = AstNode {
            node_type: NodeType::ClientInit,
            name: "boto3.client".into(),
            text: "boto3.client('s3')".into(),
            start_line: 3,
            end_line: 3,
            start_col: 0,
            end_col: 18,
            children: vec![],
            metadata: HashMap::new(),
        };
        let detection = detect(&node).unwrap();
        assert_eq!(detection.provider, CloudProvider::Aws);
        assert_eq!(detection.service, "s3");
    }

    #[test]
    fn test_detect_terraform_resource() {
        let mut metadata = HashMap::new();
        metadata.insert("resource_type".to_string(), "aws_s3_bucket".to_string());
        let node = AstNode {
            node_type: NodeType::ResourceBlock,
            name: "aws_s3_bucket.my_bucket".into(),
            text: "resource \"aws_s3_bucket\" \"my_bucket\" {}".into(),
            start_line: 1,
            end_line: 3,
            start_col: 0,
            end_col: 1,
            children: vec![],
            metadata,
        };
        let detection = detect(&node).unwrap();
        assert_eq!(detection.provider, CloudProvider::Aws);
        assert_eq!(detection.service, "s3");
    }

    #[test]
    fn test_detect_cfn_resource() {
        let mut metadata = HashMap::new();
        metadata.insert(
            "resource_type".to_string(),
            "AWS::S3::Bucket".to_string(),
        );
        let node = AstNode {
            node_type: NodeType::ResourceBlock,
            name: "AWS::S3::Bucket.MyBucket".into(),
            text: "{}".into(),
            start_line: 1,
            end_line: 1,
            start_col: 0,
            end_col: 2,
            children: vec![],
            metadata,
        };
        let detection = detect(&node).unwrap();
        assert_eq!(detection.provider, CloudProvider::Aws);
        assert_eq!(detection.service, "s3");
    }

    #[test]
    fn test_extract_boto3_service() {
        assert_eq!(extract_boto3_service("boto3.client('s3')"), "s3");
        assert_eq!(
            extract_boto3_service("boto3.resource('dynamodb')"),
            "dynamodb"
        );
    }

    #[test]
    fn test_extract_terraform_service() {
        assert_eq!(extract_terraform_service("aws_s3_bucket"), "s3");
        assert_eq!(extract_terraform_service("aws_dynamodb_table"), "dynamodb");
        assert_eq!(extract_terraform_service("aws_lambda_function"), "lambda");
    }
}
