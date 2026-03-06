use pyo3::prelude::*;
use similar::{ChangeTag, TextDiff};
use std::collections::HashMap;

use crate::parser::FileAst;

#[derive(Debug, Clone)]
pub struct DiffHunk {
    pub old_start: usize,
    pub old_count: usize,
    pub new_start: usize,
    pub new_count: usize,
    pub content: String,
}

pub fn unified_diff(old_text: &str, new_text: &str, file_path: &str) -> String {
    let diff = TextDiff::from_lines(old_text, new_text);

    let mut output = String::new();
    output.push_str(&format!("--- a/{}\n", file_path));
    output.push_str(&format!("+++ b/{}\n", file_path));

    for hunk in diff.unified_diff().header("", "").iter_hunks() {
        output.push_str(&format!("{}", hunk));
    }

    output
}

pub fn compute_hunks(old_text: &str, new_text: &str) -> Vec<DiffHunk> {
    let diff = TextDiff::from_lines(old_text, new_text);
    let mut hunks = Vec::new();

    for group in diff.grouped_ops(3) {
        let mut content = String::new();
        let mut old_start = 0;
        let mut old_count = 0;
        let mut new_start = 0;
        let mut new_count = 0;
        let mut first = true;

        for op in &group {
            if first {
                old_start = op.old_range().start + 1;
                new_start = op.new_range().start + 1;
                first = false;
            }

            for change in diff.iter_changes(op) {
                match change.tag() {
                    ChangeTag::Delete => {
                        content.push_str(&format!("-{}", change));
                        old_count += 1;
                    }
                    ChangeTag::Insert => {
                        content.push_str(&format!("+{}", change));
                        new_count += 1;
                    }
                    ChangeTag::Equal => {
                        content.push_str(&format!(" {}", change));
                        old_count += 1;
                        new_count += 1;
                    }
                }
            }
        }

        hunks.push(DiffHunk {
            old_start,
            old_count,
            new_start,
            new_count,
            content,
        });
    }

    hunks
}

pub fn ast_diff(old_ast: &FileAst, new_ast: &FileAst) -> Vec<AstChange> {
    let mut changes = Vec::new();

    // Compare nodes by type and name
    let old_nodes: HashMap<(String, &str), &crate::parser::AstNode> = old_ast
        .nodes
        .iter()
        .map(|n| ((n.node_type.as_str().to_string(), n.name.as_str()), n))
        .collect();

    let new_nodes: HashMap<(String, &str), &crate::parser::AstNode> = new_ast
        .nodes
        .iter()
        .map(|n| ((n.node_type.as_str().to_string(), n.name.as_str()), n))
        .collect();

    // Find removed nodes
    for (key, old_node) in &old_nodes {
        if !new_nodes.contains_key(key) {
            changes.push(AstChange {
                change_type: "removed".to_string(),
                node_type: key.0.clone(),
                node_name: key.1.to_string(),
                old_text: Some(old_node.text.clone()),
                new_text: None,
            });
        }
    }

    // Find added nodes
    for (key, new_node) in &new_nodes {
        if !old_nodes.contains_key(key) {
            changes.push(AstChange {
                change_type: "added".to_string(),
                node_type: key.0.clone(),
                node_name: key.1.to_string(),
                old_text: None,
                new_text: Some(new_node.text.clone()),
            });
        }
    }

    // Find modified nodes
    for (key, old_node) in &old_nodes {
        if let Some(new_node) = new_nodes.get(key) {
            if old_node.text != new_node.text {
                changes.push(AstChange {
                    change_type: "modified".to_string(),
                    node_type: key.0.clone(),
                    node_name: key.1.to_string(),
                    old_text: Some(old_node.text.clone()),
                    new_text: Some(new_node.text.clone()),
                });
            }
        }
    }

    changes
}

#[derive(Debug, Clone)]
pub struct AstChange {
    pub change_type: String,
    pub node_type: String,
    pub node_name: String,
    pub old_text: Option<String>,
    pub new_text: Option<String>,
}

#[pyfunction]
pub fn py_unified_diff(old_text: String, new_text: String, file_path: String) -> String {
    unified_diff(&old_text, &new_text, &file_path)
}

#[pyfunction]
pub fn py_ast_diff(
    old_nodes: Vec<crate::parser::PyAstNode>,
    new_nodes: Vec<crate::parser::PyAstNode>,
    file_path: String,
) -> Vec<HashMap<String, String>> {
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

    ast_diff(&old_ast, &new_ast)
        .into_iter()
        .map(|c| {
            let mut m = HashMap::new();
            m.insert("change_type".into(), c.change_type);
            m.insert("node_type".into(), c.node_type);
            m.insert("node_name".into(), c.node_name);
            if let Some(old) = c.old_text {
                m.insert("old_text".into(), old);
            }
            if let Some(new) = c.new_text {
                m.insert("new_text".into(), new);
            }
            m
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unified_diff() {
        let old = "import boto3\ns3 = boto3.client('s3')\n";
        let new = "from google.cloud import storage\nclient = storage.Client()\n";
        let diff = unified_diff(old, new, "test.py");
        assert!(diff.contains("--- a/test.py"));
        assert!(diff.contains("+++ b/test.py"));
        assert!(diff.contains("-import boto3"));
        assert!(diff.contains("+from google.cloud import storage"));
    }

    #[test]
    fn test_compute_hunks() {
        let old = "line1\nline2\nline3\n";
        let new = "line1\nmodified\nline3\n";
        let hunks = compute_hunks(old, new);
        assert!(!hunks.is_empty());
    }
}
