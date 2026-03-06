use std::collections::HashMap;
use thiserror::Error;

use super::{PyAstNode, PyFileAst};

#[derive(Debug, Clone, PartialEq)]
pub enum Language {
    Python,
    TypeScript,
    Hcl,
    CloudFormation,
}

impl Language {
    pub fn from_str(s: &str) -> Result<Self, String> {
        match s.to_lowercase().as_str() {
            "python" | "py" => Ok(Language::Python),
            "typescript" | "ts" | "javascript" | "js" => Ok(Language::TypeScript),
            "hcl" | "terraform" | "tf" => Ok(Language::Hcl),
            "cloudformation" | "cfn" => Ok(Language::CloudFormation),
            _ => Err(format!("Unsupported language: {}", s)),
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Language::Python => "python",
            Language::TypeScript => "typescript",
            Language::Hcl => "hcl",
            Language::CloudFormation => "cloudformation",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum NodeType {
    Import,
    FunctionCall,
    ClientInit,
    ResourceBlock,
    MethodCall,
    StringLiteral,
    VariableAssignment,
    EnvVar,
    Other,
}

impl NodeType {
    pub fn as_str(&self) -> &'static str {
        match self {
            NodeType::Import => "import",
            NodeType::FunctionCall => "function_call",
            NodeType::ClientInit => "client_init",
            NodeType::ResourceBlock => "resource_block",
            NodeType::MethodCall => "method_call",
            NodeType::StringLiteral => "string_literal",
            NodeType::VariableAssignment => "variable_assignment",
            NodeType::EnvVar => "env_var",
            NodeType::Other => "other",
        }
    }
}

#[derive(Debug, Clone)]
pub struct AstNode {
    pub node_type: NodeType,
    pub name: String,
    pub text: String,
    pub start_line: usize,
    pub end_line: usize,
    pub start_col: usize,
    pub end_col: usize,
    pub children: Vec<AstNode>,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct FileAst {
    pub file_path: String,
    pub language: Language,
    pub nodes: Vec<AstNode>,
}

impl From<AstNode> for PyAstNode {
    fn from(node: AstNode) -> Self {
        PyAstNode {
            node_type: node.node_type.as_str().to_string(),
            name: node.name,
            text: node.text,
            start_line: node.start_line,
            end_line: node.end_line,
            start_col: node.start_col,
            end_col: node.end_col,
            children: node.children.into_iter().map(|c| c.into()).collect(),
            metadata: node.metadata,
        }
    }
}

impl From<FileAst> for PyFileAst {
    fn from(ast: FileAst) -> Self {
        PyFileAst {
            file_path: ast.file_path,
            language: ast.language.as_str().to_string(),
            nodes: ast.nodes.into_iter().map(|n| n.into()).collect(),
        }
    }
}

#[derive(Debug, Error)]
pub enum ParseError {
    #[error("Unsupported language: {0}")]
    UnsupportedLanguage(String),
    #[error("Parse error: {0}")]
    TreeSitterError(String),
    #[error("IO error: {0}")]
    IoError(String),
    #[error("Invalid source: {0}")]
    InvalidSource(String),
}
