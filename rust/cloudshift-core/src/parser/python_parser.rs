use std::collections::HashMap;

use tree_sitter::{Node, Parser};

use super::ast_types::*;

pub fn parse(source: &str, file_path: String) -> Result<FileAst, ParseError> {
    let mut parser = Parser::new();
    let language = tree_sitter_python::LANGUAGE;
    parser
        .set_language(&language.into())
        .map_err(|e| ParseError::TreeSitterError(e.to_string()))?;

    let tree = parser
        .parse(source, None)
        .ok_or_else(|| ParseError::TreeSitterError("Failed to parse Python source".into()))?;

    let root = tree.root_node();
    let mut nodes = Vec::new();
    extract_nodes(root, source, &mut nodes);

    Ok(FileAst {
        file_path,
        language: Language::Python,
        nodes,
    })
}

fn extract_nodes(node: Node, source: &str, nodes: &mut Vec<AstNode>) {
    match node.kind() {
        "import_statement" | "import_from_statement" => {
            let text = node_text(node, source);
            let name = extract_import_name(node, source);
            let mut metadata = HashMap::new();
            if node.kind() == "import_from_statement" {
                if let Some(module) = node.child_by_field_name("module_name") {
                    metadata.insert("module".to_string(), node_text(module, source));
                }
            }
            nodes.push(AstNode {
                node_type: NodeType::Import,
                name,
                text,
                start_line: node.start_position().row + 1,
                end_line: node.end_position().row + 1,
                start_col: node.start_position().column,
                end_col: node.end_position().column,
                children: vec![],
                metadata,
            });
        }
        "call" => {
            let text = node_text(node, source);
            let name = extract_call_name(node, source);
            let call_type = classify_call(&name, &text);
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
        "assignment" => {
            let text = node_text(node, source);
            let name = node
                .child_by_field_name("left")
                .map(|n| node_text(n, source))
                .unwrap_or_default();
            // Check for env var patterns
            let node_type = if text.contains("os.environ") || text.contains("os.getenv") {
                NodeType::EnvVar
            } else {
                NodeType::VariableAssignment
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
        "string" | "concatenated_string" => {
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

fn extract_import_name(node: Node, source: &str) -> String {
    if node.kind() == "import_from_statement" {
        if let Some(module) = node.child_by_field_name("module_name") {
            return node_text(module, source);
        }
    }
    // For plain import, get the module name
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "dotted_name" || child.kind() == "aliased_import" {
            return node_text(child, source);
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

fn classify_call(name: &str, _text: &str) -> NodeType {
    let client_patterns = [
        "boto3.client",
        "boto3.resource",
        "boto3.Session",
        "BlobServiceClient",
        "ServiceBusClient",
        "CosmosClient",
    ];
    for pattern in &client_patterns {
        if name.contains(pattern) {
            return NodeType::ClientInit;
        }
    }
    if name.contains('.') {
        NodeType::MethodCall
    } else {
        NodeType::FunctionCall
    }
}

fn looks_like_cloud_reference(text: &str) -> bool {
    text.contains("arn:aws:")
        || text.contains("amazonaws.com")
        || text.contains(".azure.")
        || text.contains("management.azure.com")
        || text.contains("us-east-")
        || text.contains("us-west-")
        || text.contains("eu-west-")
        || text.contains("ap-southeast-")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_boto3_imports() {
        let source = r#"
import boto3
from botocore.config import Config

client = boto3.client('s3')
"#;
        let ast = parse(source, "test.py".into()).unwrap();
        assert_eq!(ast.language, Language::Python);

        let imports: Vec<_> = ast
            .nodes
            .iter()
            .filter(|n| matches!(n.node_type, NodeType::Import))
            .collect();
        assert_eq!(imports.len(), 2);
    }

    #[test]
    fn test_parse_client_init() {
        let source = r#"
import boto3
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
"#;
        let ast = parse(source, "test.py".into()).unwrap();
        let client_inits: Vec<_> = ast
            .nodes
            .iter()
            .filter(|n| matches!(n.node_type, NodeType::ClientInit))
            .collect();
        assert_eq!(client_inits.len(), 2);
    }

    #[test]
    fn test_parse_arn_string() {
        let source = r#"
arn = "arn:aws:s3:::my-bucket"
"#;
        let ast = parse(source, "test.py".into()).unwrap();
        let strings: Vec<_> = ast
            .nodes
            .iter()
            .filter(|n| matches!(n.node_type, NodeType::StringLiteral))
            .collect();
        assert_eq!(strings.len(), 1);
    }
}
