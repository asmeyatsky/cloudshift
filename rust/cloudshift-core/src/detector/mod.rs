mod aws;
mod azure;

use pyo3::prelude::*;
use std::collections::HashMap;

use crate::parser::{AstNode, FileAst, NodeType};

#[derive(Debug, Clone, PartialEq)]
pub enum CloudProvider {
    Aws,
    Azure,
    Gcp,
    Unknown,
}

impl CloudProvider {
    pub fn as_str(&self) -> &'static str {
        match self {
            CloudProvider::Aws => "aws",
            CloudProvider::Azure => "azure",
            CloudProvider::Gcp => "gcp",
            CloudProvider::Unknown => "unknown",
        }
    }
}

#[derive(Debug, Clone)]
pub struct ServiceDetection {
    pub provider: CloudProvider,
    pub service: String,
    pub construct_type: String,
    pub confidence: f64,
    pub node_name: String,
    pub start_line: usize,
    pub end_line: usize,
    pub metadata: HashMap<String, String>,
}

#[pyclass(frozen, from_py_object)]
#[derive(Clone, Debug)]
pub struct PyServiceDetection {
    #[pyo3(get)]
    pub provider: String,
    #[pyo3(get)]
    pub service: String,
    #[pyo3(get)]
    pub construct_type: String,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub node_name: String,
    #[pyo3(get)]
    pub start_line: usize,
    #[pyo3(get)]
    pub end_line: usize,
    #[pyo3(get)]
    pub metadata: HashMap<String, String>,
}

impl From<ServiceDetection> for PyServiceDetection {
    fn from(d: ServiceDetection) -> Self {
        PyServiceDetection {
            provider: d.provider.as_str().to_string(),
            service: d.service,
            construct_type: d.construct_type,
            confidence: d.confidence,
            node_name: d.node_name,
            start_line: d.start_line,
            end_line: d.end_line,
            metadata: d.metadata,
        }
    }
}

pub fn detect_services(ast: &FileAst) -> Vec<ServiceDetection> {
    let mut detections = Vec::new();

    for node in &ast.nodes {
        // Try AWS detection
        if let Some(detection) = aws::detect(node) {
            detections.push(detection);
            continue;
        }
        // Try Azure detection
        if let Some(detection) = azure::detect(node) {
            detections.push(detection);
        }
    }

    detections
}

pub fn detect_from_node(node: &AstNode) -> Option<ServiceDetection> {
    aws::detect(node).or_else(|| azure::detect(node))
}

#[pyfunction]
pub fn py_detect_services(nodes: Vec<crate::parser::PyAstNode>) -> Vec<PyServiceDetection> {
    let ast_nodes: Vec<AstNode> = nodes.into_iter().map(py_node_to_ast_node).collect();
    let file_ast = FileAst {
        file_path: String::new(),
        language: crate::parser::ast_types::Language::Python,
        nodes: ast_nodes,
    };
    detect_services(&file_ast)
        .into_iter()
        .map(|d| d.into())
        .collect()
}

pub fn py_node_to_ast_node(py: crate::parser::PyAstNode) -> AstNode {
    AstNode {
        node_type: match py.node_type.as_str() {
            "import" => NodeType::Import,
            "function_call" => NodeType::FunctionCall,
            "client_init" => NodeType::ClientInit,
            "resource_block" => NodeType::ResourceBlock,
            "method_call" => NodeType::MethodCall,
            "string_literal" => NodeType::StringLiteral,
            "variable_assignment" => NodeType::VariableAssignment,
            "env_var" => NodeType::EnvVar,
            _ => NodeType::Other,
        },
        name: py.name,
        text: py.text,
        start_line: py.start_line,
        end_line: py.end_line,
        start_col: py.start_col,
        end_col: py.end_col,
        children: py.children.into_iter().map(py_node_to_ast_node).collect(),
        metadata: py.metadata,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_empty() {
        let ast = FileAst {
            file_path: "test.py".into(),
            language: crate::parser::Language::Python,
            nodes: vec![],
        };
        assert!(detect_services(&ast).is_empty());
    }
}
