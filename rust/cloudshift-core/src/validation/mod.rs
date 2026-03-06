use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;

use crate::parser::FileAst;

#[pyclass(frozen, from_py_object)]
#[derive(Clone, Debug)]
pub struct PyValidationResult {
    #[pyo3(get)]
    pub is_valid: bool,
    #[pyo3(get)]
    pub issues: Vec<HashMap<String, String>>,
    #[pyo3(get)]
    pub summary: String,
}

#[derive(Debug, Clone)]
pub struct ValidationIssue {
    pub severity: IssueSeverity,
    pub category: String,
    pub message: String,
    pub file_path: String,
    pub line: usize,
    pub suggestion: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum IssueSeverity {
    Error,
    Warning,
    Info,
}

impl IssueSeverity {
    pub fn as_str(&self) -> &'static str {
        match self {
            IssueSeverity::Error => "error",
            IssueSeverity::Warning => "warning",
            IssueSeverity::Info => "info",
        }
    }
}

pub fn check_ast_equivalence(old_ast: &FileAst, new_ast: &FileAst) -> Vec<ValidationIssue> {
    let mut issues = Vec::new();

    // Check that all non-cloud constructs are preserved
    let old_non_cloud: Vec<_> = old_ast
        .nodes
        .iter()
        .filter(|n| !is_cloud_construct(n))
        .collect();

    let new_non_cloud: Vec<_> = new_ast
        .nodes
        .iter()
        .filter(|n| !is_cloud_construct(n))
        .collect();

    // Check for missing non-cloud constructs
    for old_node in &old_non_cloud {
        let found = new_non_cloud.iter().any(|n| {
            n.node_type.as_str() == old_node.node_type.as_str()
                && n.name == old_node.name
        });
        if !found {
            issues.push(ValidationIssue {
                severity: IssueSeverity::Warning,
                category: "ast_equivalence".to_string(),
                message: format!(
                    "Non-cloud construct '{}' ({}) may have been accidentally removed",
                    old_node.name,
                    old_node.node_type.as_str()
                ),
                file_path: old_ast.file_path.clone(),
                line: old_node.start_line,
                suggestion: "Verify this construct should have been removed".to_string(),
            });
        }
    }

    issues
}

pub fn scan_residual_references(source: &str, file_path: &str) -> Vec<ValidationIssue> {
    let mut issues = Vec::new();

    let patterns: Vec<(&str, &str, &str)> = vec![
        // AWS patterns
        (r"arn:aws:[a-z0-9\-]+:[a-z0-9\-]*:\d*:", "aws_arn", "AWS ARN reference found"),
        (r"amazonaws\.com", "aws_endpoint", "AWS endpoint reference found"),
        (r"import\s+boto3", "aws_import", "boto3 import still present"),
        (r"from\s+botocore", "aws_import", "botocore import still present"),
        (r"@aws-sdk/", "aws_import", "AWS SDK import still present"),
        (r"aws_[a-z_]+\s*\.", "aws_terraform", "AWS Terraform resource reference found"),
        (r"AWS::", "aws_cfn", "CloudFormation resource type reference found"),
        (r"us-east-\d|us-west-\d|eu-west-\d|ap-southeast-\d", "aws_region", "AWS region reference found"),
        (r"AWS_ACCESS_KEY|AWS_SECRET_ACCESS|AWS_SESSION_TOKEN|AWS_REGION|AWS_DEFAULT_REGION", "aws_env", "AWS environment variable reference found"),
        // Azure patterns
        (r"from\s+azure\.", "azure_import", "Azure SDK import still present"),
        (r"@azure/", "azure_import", "Azure SDK import still present"),
        (r"azurerm_", "azure_terraform", "Azure Terraform resource reference found"),
        (r"Microsoft\.\w+/", "azure_arm", "Azure ARM resource type reference found"),
        (r"\.azure\.com|\.azure\.net", "azure_endpoint", "Azure endpoint reference found"),
        (r"AZURE_CLIENT_ID|AZURE_TENANT_ID|AZURE_SUBSCRIPTION_ID", "azure_env", "Azure environment variable reference found"),
    ];

    for (pattern, category, message) in &patterns {
        let re = Regex::new(pattern).unwrap();
        for (line_num, line) in source.lines().enumerate() {
            if re.is_match(line) {
                // Skip comments
                let trimmed = line.trim();
                if trimmed.starts_with('#') || trimmed.starts_with("//") || trimmed.starts_with("/*") {
                    continue;
                }
                issues.push(ValidationIssue {
                    severity: IssueSeverity::Error,
                    category: category.to_string(),
                    message: message.to_string(),
                    file_path: file_path.to_string(),
                    line: line_num + 1,
                    suggestion: format!("Replace or remove: {}", line.trim()),
                });
            }
        }
    }

    issues
}

fn is_cloud_construct(node: &crate::parser::ast_types::AstNode) -> bool {
    let cloud_indicators = [
        "boto3", "botocore", "aws", "azure", "@aws-sdk", "@azure",
        "s3", "dynamodb", "lambda", "sqs", "sns",
        "BlobServiceClient", "ServiceBusClient", "CosmosClient",
    ];
    cloud_indicators.iter().any(|indicator| {
        node.name.contains(indicator) || node.text.contains(indicator)
    })
}

#[pyfunction]
pub fn py_check_ast_equivalence(
    old_nodes: Vec<crate::parser::PyAstNode>,
    new_nodes: Vec<crate::parser::PyAstNode>,
    file_path: String,
) -> PyValidationResult {
    let old_ast = FileAst {
        file_path: file_path.clone(),
        language: crate::parser::Language::Python,
        nodes: old_nodes
            .into_iter()
            .map(crate::detector::py_node_to_ast_node)
            .collect(),
    };
    let new_ast = FileAst {
        file_path,
        language: crate::parser::Language::Python,
        nodes: new_nodes
            .into_iter()
            .map(crate::detector::py_node_to_ast_node)
            .collect(),
    };

    let issues = check_ast_equivalence(&old_ast, &new_ast);
    let is_valid = issues.iter().all(|i| i.severity != IssueSeverity::Error);

    PyValidationResult {
        is_valid,
        issues: issues.iter().map(issue_to_map).collect(),
        summary: format!(
            "{} issues found ({} errors, {} warnings)",
            issues.len(),
            issues.iter().filter(|i| i.severity == IssueSeverity::Error).count(),
            issues.iter().filter(|i| i.severity == IssueSeverity::Warning).count(),
        ),
    }
}

#[pyfunction]
pub fn py_scan_residual_refs(source: String, file_path: String) -> PyValidationResult {
    let issues = scan_residual_references(&source, &file_path);
    let is_valid = issues.is_empty();

    PyValidationResult {
        is_valid,
        issues: issues.iter().map(issue_to_map).collect(),
        summary: format!("{} residual references found", issues.len()),
    }
}

fn issue_to_map(issue: &ValidationIssue) -> HashMap<String, String> {
    let mut m = HashMap::new();
    m.insert("severity".into(), issue.severity.as_str().to_string());
    m.insert("category".into(), issue.category.clone());
    m.insert("message".into(), issue.message.clone());
    m.insert("file_path".into(), issue.file_path.clone());
    m.insert("line".into(), issue.line.to_string());
    m.insert("suggestion".into(), issue.suggestion.clone());
    m
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scan_residual_aws_references() {
        let source = r#"
from google.cloud import storage
client = storage.Client()
bucket_arn = "arn:aws:s3:::my-bucket"
endpoint = "s3.amazonaws.com"
"#;
        let issues = scan_residual_references(source, "test.py");
        assert!(issues.len() >= 2); // ARN + endpoint
    }

    #[test]
    fn test_scan_clean_gcp_code() {
        let source = r#"
from google.cloud import storage
client = storage.Client()
bucket = client.bucket("my-bucket")
"#;
        let issues = scan_residual_references(source, "test.py");
        assert!(issues.is_empty());
    }

    #[test]
    fn test_scan_residual_azure_references() {
        let source = r#"
from google.cloud import storage
url = "https://mystorageaccount.blob.core.windows.azure.net"
"#;
        let issues = scan_residual_references(source, "test.py");
        assert!(!issues.is_empty());
    }
}
