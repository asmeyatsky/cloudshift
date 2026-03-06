use std::collections::HashMap;

use tree_sitter::{Node, Parser};

use super::ast_types::*;

pub fn parse(source: &str, file_path: String) -> Result<FileAst, ParseError> {
    let mut parser = Parser::new();
    let language = tree_sitter_hcl::LANGUAGE;
    parser
        .set_language(&language.into())
        .map_err(|e| ParseError::TreeSitterError(e.to_string()))?;

    let tree = parser
        .parse(source, None)
        .ok_or_else(|| ParseError::TreeSitterError("Failed to parse HCL source".into()))?;

    let root = tree.root_node();
    let mut nodes = Vec::new();
    extract_blocks(root, source, &mut nodes);

    Ok(FileAst {
        file_path,
        language: Language::Hcl,
        nodes,
    })
}

fn extract_blocks(node: Node, source: &str, nodes: &mut Vec<AstNode>) {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        match child.kind() {
            "block" => {
                if let Some(block_node) = parse_block(child, source) {
                    nodes.push(block_node);
                }
            }
            "body" | "config_file" => {
                extract_blocks(child, source, nodes);
            }
            _ => {}
        }
    }
}

fn parse_block(node: Node, source: &str) -> Option<AstNode> {
    let text = node_text(node, source);
    let mut cursor = node.walk();
    let children_nodes: Vec<_> = node.children(&mut cursor).collect();

    // First child is the block type (resource, data, variable, etc.)
    let block_type = children_nodes
        .first()
        .map(|n| node_text(*n, source))
        .unwrap_or_default();

    // Collect string labels (skip the first identifier which is the block type)
    let labels: Vec<String> = children_nodes
        .iter()
        .filter(|n| n.kind() == "string_lit")
        .map(|n| {
            let t = node_text(*n, source);
            t.trim_matches('"').to_string()
        })
        .collect();

    let (resource_type, resource_name) = match block_type.as_str() {
        "resource" | "data" => {
            let rtype = labels.first().cloned().unwrap_or_default();
            let rname = labels.get(1).cloned().unwrap_or_default();
            (rtype, rname)
        }
        "variable" | "output" | "locals" | "module" | "provider" => {
            let rname = labels.first().cloned().unwrap_or_default();
            (block_type.clone(), rname)
        }
        _ => (block_type.clone(), String::new()),
    };

    let mut metadata = HashMap::new();
    metadata.insert("block_type".to_string(), block_type);
    if !resource_type.is_empty() {
        metadata.insert("resource_type".to_string(), resource_type.clone());
    }

    let name = if resource_name.is_empty() {
        resource_type.clone()
    } else {
        format!("{}.{}", resource_type, resource_name)
    };

    Some(AstNode {
        node_type: NodeType::ResourceBlock,
        name,
        text,
        start_line: node.start_position().row + 1,
        end_line: node.end_position().row + 1,
        start_col: node.start_position().column,
        end_col: node.end_position().column,
        children: vec![],
        metadata,
    })
}

fn node_text(node: Node, source: &str) -> String {
    source[node.byte_range()].to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_aws_resource() {
        let source = r#"
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-app-bucket"
  acl    = "private"
}

resource "aws_dynamodb_table" "my_table" {
  name     = "my-table"
  hash_key = "id"
}
"#;
        let ast = parse(source, "main.tf".into()).unwrap();
        assert_eq!(ast.language, Language::Hcl);
        let resources: Vec<_> = ast
            .nodes
            .iter()
            .filter(|n| matches!(n.node_type, NodeType::ResourceBlock))
            .collect();
        assert_eq!(resources.len(), 2);
    }

    #[test]
    fn test_parse_provider_block() {
        let source = r#"
provider "aws" {
  region = "us-east-1"
}
"#;
        let ast = parse(source, "provider.tf".into()).unwrap();
        assert!(!ast.nodes.is_empty());
    }
}
