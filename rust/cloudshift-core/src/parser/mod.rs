mod python_parser;
mod typescript_parser;
mod hcl_parser;
mod cfn_parser;
pub mod ast_types;

pub use ast_types::*;

use pyo3::prelude::*;
use std::path::Path;

#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct PyFileAst {
    #[pyo3(get)]
    pub file_path: String,
    #[pyo3(get)]
    pub language: String,
    #[pyo3(get)]
    pub nodes: Vec<PyAstNode>,
}

#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct PyAstNode {
    #[pyo3(get)]
    pub node_type: String,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub start_line: usize,
    #[pyo3(get)]
    pub end_line: usize,
    #[pyo3(get)]
    pub start_col: usize,
    #[pyo3(get)]
    pub end_col: usize,
    #[pyo3(get)]
    pub children: Vec<PyAstNode>,
    #[pyo3(get)]
    pub metadata: std::collections::HashMap<String, String>,
}

#[pymethods]
impl PyFileAst {
    #[new]
    pub fn new(file_path: String, language: String, nodes: Vec<PyAstNode>) -> Self {
        Self { file_path, language, nodes }
    }

    fn __repr__(&self) -> String {
        format!("FileAst(path='{}', lang='{}', nodes={})", self.file_path, self.language, self.nodes.len())
    }
}

#[pymethods]
impl PyAstNode {
    #[new]
    #[pyo3(signature = (node_type, name, text, start_line, end_line, start_col=0, end_col=0, children=vec![], metadata=std::collections::HashMap::new()))]
    pub fn new(
        node_type: String,
        name: String,
        text: String,
        start_line: usize,
        end_line: usize,
        start_col: usize,
        end_col: usize,
        children: Vec<PyAstNode>,
        metadata: std::collections::HashMap<String, String>,
    ) -> Self {
        Self { node_type, name, text, start_line, end_line, start_col, end_col, children, metadata }
    }

    fn __repr__(&self) -> String {
        format!("AstNode(type='{}', name='{}', lines={}-{})", self.node_type, self.name, self.start_line, self.end_line)
    }
}

pub fn detect_language(path: &Path) -> Option<Language> {
    match path.extension()?.to_str()? {
        "py" => Some(Language::Python),
        "ts" | "tsx" | "js" | "jsx" => Some(Language::TypeScript),
        "tf" | "hcl" => Some(Language::Hcl),
        "json" => {
            // Check if it's a CloudFormation template
            if let Ok(content) = std::fs::read_to_string(path) {
                if content.contains("AWSTemplateFormatVersion") || content.contains("aws-cdk") {
                    return Some(Language::CloudFormation);
                }
            }
            None
        }
        "yaml" | "yml" => {
            if let Ok(content) = std::fs::read_to_string(path) {
                if content.contains("AWSTemplateFormatVersion") {
                    return Some(Language::CloudFormation);
                }
            }
            None
        }
        _ => None,
    }
}

pub fn parse_file(path: &Path) -> Result<FileAst, ParseError> {
    let language = detect_language(path).ok_or_else(|| ParseError::UnsupportedLanguage(
        path.extension().map(|e| e.to_string_lossy().to_string()).unwrap_or_default()
    ))?;
    let source = std::fs::read_to_string(path)
        .map_err(|e| ParseError::IoError(e.to_string()))?;
    parse_source(&source, language, path.to_string_lossy().to_string())
}

pub fn parse_source(source: &str, language: Language, file_path: String) -> Result<FileAst, ParseError> {
    match language {
        Language::Python => python_parser::parse(source, file_path),
        Language::TypeScript => typescript_parser::parse(source, file_path),
        Language::Hcl => hcl_parser::parse(source, file_path),
        Language::CloudFormation => cfn_parser::parse(source, file_path),
    }
}

#[pyfunction]
pub fn py_parse_file(path: String) -> PyResult<PyFileAst> {
    let ast = parse_file(Path::new(&path))
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(ast.into())
}

#[pyfunction]
pub fn py_parse_source(source: String, language: String, file_path: String) -> PyResult<PyFileAst> {
    let lang = Language::from_str(&language)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))?;
    let ast = parse_source(&source, lang, file_path)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(ast.into())
}
