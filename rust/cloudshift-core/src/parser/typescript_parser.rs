use std::collections::HashMap;

use tree_sitter::{Node, Parser};

use super::ast_types::*;

pub fn parse(source: &str, file_path: String) -> Result<FileAst, ParseError> {
    let mut parser = Parser::new();
    let language = tree_sitter_typescript::LANGUAGE_TYPESCRIPT;
    parser
        .set_language(&language.into())
        .map_err(|e| ParseError::TreeSitterError(e.to_string()))?;

    let tree = parser
        .parse(source, None)
        .ok_or_else(|| ParseError::TreeSitterError("Failed to parse TypeScript source".into()))?;

    let root = tree.root_node();
    let mut nodes = Vec::new();
    extract_nodes(root, source, &mut nodes);

    Ok(FileAst {
        file_path,
        language: Language::TypeScript,
        nodes,
    })
}

fn extract_nodes(node: Node, source: &str, nodes: &mut Vec<AstNode>) {
    match node.kind() {
        "import_statement" => {
            let text = node_text(node, source);
            let name = extract_import_source(node, source);
            nodes.push(AstNode {
                node_type: NodeType::Import,
                name,
                text,
                start_line: node.start_position().row + 1,
                end_line: node.end_position().row + 1,
                start_col: node.start_position().column,
                end_col: node.end_position().column,
                children: vec![],
                metadata: HashMap::new(),
            });
        }
        "call_expression" => {
            let text = node_text(node, source);
            let name = extract_call_name(node, source);
            let call_type = classify_call(&name);
            nodes.push(AstNode {
                node_type: call_type,
                name,
                text,
                start_line: node.start_position().row + 1,
                end_line: node.end_position().row + 1,
                start_col: node.start_position().column,
                end_col: node.end_position().column,
                children: vec![],
                metadata: HashMap::new(),
            });
        }
        "new_expression" => {
            let text = node_text(node, source);
            let name = extract_constructor_name(node, source);
            let node_type = if is_cloud_client(&name) {
                NodeType::ClientInit
            } else {
                NodeType::FunctionCall
            };
            nodes.push(AstNode {
                node_type,
                name,
                text,
                start_line: node.start_position().row + 1,
                end_line: node.end_position().row + 1,
                start_col: node.start_position().column,
                end_col: node.end_position().column,
                children: vec![],
                metadata: HashMap::new(),
            });
        }
        "variable_declarator" => {
            let text = node_text(node, source);
            if text.contains("process.env") {
                let name = node
                    .child_by_field_name("name")
                    .map(|n| node_text(n, source))
                    .unwrap_or_default();
                nodes.push(AstNode {
                    node_type: NodeType::EnvVar,
                    name,
                    text,
                    start_line: node.start_position().row + 1,
                    end_line: node.end_position().row + 1,
                    start_col: node.start_position().column,
                    end_col: node.end_position().column,
                    children: vec![],
                    metadata: HashMap::new(),
                });
            }
        }
        "string" | "template_string" => {
            let text = node_text(node, source);
            if looks_like_cloud_reference(&text) {
                nodes.push(AstNode {
                    node_type: NodeType::StringLiteral,
                    name: String::new(),
                    text,
                    start_line: node.start_position().row + 1,
                    end_line: node.end_position().row + 1,
                    start_col: node.start_position().column,
                    end_col: node.end_position().column,
                    children: vec![],
                    metadata: HashMap::new(),
                });
            }
        }
        _ => {}
    }

    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        extract_nodes(child, source, nodes);
    }
}

fn node_text(node: Node, source: &str) -> String {
    source[node.byte_range()].to_string()
}

fn extract_import_source(node: Node, source: &str) -> String {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "string" {
            let text = node_text(child, source);
            return text.trim_matches('\'').trim_matches('"').to_string();
        }
    }
    node_text(node, source)
}

fn extract_call_name(node: Node, source: &str) -> String {
    if let Some(func) = node.child_by_field_name("function") {
        node_text(func, source)
    } else {
        String::new()
    }
}

fn extract_constructor_name(node: Node, source: &str) -> String {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "identifier" || child.kind() == "member_expression" {
            return node_text(child, source);
        }
    }
    String::new()
}

fn classify_call(name: &str) -> NodeType {
    if is_cloud_client(name) {
        NodeType::ClientInit
    } else if name.contains('.') {
        NodeType::MethodCall
    } else {
        NodeType::FunctionCall
    }
}

fn is_cloud_client(name: &str) -> bool {
    let patterns = [
        "S3Client",
        "DynamoDBClient",
        "LambdaClient",
        "SQSClient",
        "SNSClient",
        "EC2Client",
        "BlobServiceClient",
        "ServiceBusClient",
        "CosmosClient",
    ];
    patterns.iter().any(|p| name.contains(p))
}

fn looks_like_cloud_reference(text: &str) -> bool {
    text.contains("arn:aws:")
        || text.contains("amazonaws.com")
        || text.contains(".azure.")
        || text.contains("management.azure.com")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_aws_sdk_imports() {
        let source = r#"
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
"#;
        let ast = parse(source, "test.ts".into()).unwrap();
        assert_eq!(ast.language, Language::TypeScript);
        let imports: Vec<_> = ast
            .nodes
            .iter()
            .filter(|n| matches!(n.node_type, NodeType::Import))
            .collect();
        assert_eq!(imports.len(), 2);
    }

    #[test]
    fn test_parse_client_constructor() {
        let source = r#"
import { S3Client } from "@aws-sdk/client-s3";
const client = new S3Client({ region: "us-east-1" });
"#;
        let ast = parse(source, "test.ts".into()).unwrap();
        let inits: Vec<_> = ast
            .nodes
            .iter()
            .filter(|n| matches!(n.node_type, NodeType::ClientInit))
            .collect();
        assert_eq!(inits.len(), 1);
    }
}
