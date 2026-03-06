use pyo3::prelude::*;
use std::collections::HashMap;
use std::path::Path;

use ignore::WalkBuilder;

use crate::parser;

pub fn walk_directory(root: &str) -> Vec<String> {
    let mut files = Vec::new();

    let walker = WalkBuilder::new(root)
        .hidden(true) // respect hidden files
        .git_ignore(true) // respect .gitignore
        .build();

    for entry in walker {
        if let Ok(entry) = entry {
            let path = entry.path();
            if path.is_file() {
                if parser::detect_language(path).is_some() {
                    files.push(path.to_string_lossy().to_string());
                }
            }
        }
    }

    files
}

#[derive(Debug, Clone, Default)]
pub struct DependencyGraph {
    pub nodes: Vec<String>,
    pub edges: Vec<(usize, usize)>,
    pub adjacency: HashMap<usize, Vec<usize>>,
}

impl DependencyGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_node(&mut self, path: String) -> usize {
        if let Some(idx) = self.nodes.iter().position(|n| n == &path) {
            return idx;
        }
        let idx = self.nodes.len();
        self.nodes.push(path);
        idx
    }

    pub fn add_edge(&mut self, from: usize, to: usize) {
        self.edges.push((from, to));
        self.adjacency.entry(from).or_default().push(to);
    }

    pub fn topological_sort(&self) -> Vec<usize> {
        let n = self.nodes.len();
        let mut in_degree = vec![0usize; n];
        for &(_, to) in &self.edges {
            if to < n {
                in_degree[to] += 1;
            }
        }

        let mut queue: Vec<usize> = (0..n).filter(|&i| in_degree[i] == 0).collect();
        let mut result = Vec::new();

        while let Some(node) = queue.pop() {
            result.push(node);
            if let Some(neighbors) = self.adjacency.get(&node) {
                for &neighbor in neighbors {
                    if neighbor < n {
                        in_degree[neighbor] -= 1;
                        if in_degree[neighbor] == 0 {
                            queue.push(neighbor);
                        }
                    }
                }
            }
        }

        // If there are cycles, append remaining nodes
        if result.len() < n {
            for i in 0..n {
                if !result.contains(&i) {
                    result.push(i);
                }
            }
        }

        result
    }
}

pub fn build_dependency_graph(files: &[String]) -> DependencyGraph {
    let mut graph = DependencyGraph::new();

    // Add all files as nodes
    for file in files {
        graph.add_node(file.clone());
    }

    // Build a lookup for relative imports
    let file_set: HashMap<&str, usize> = files
        .iter()
        .enumerate()
        .map(|(i, f)| (f.as_str(), i))
        .collect();

    // For each file, parse and find imports to build edges
    for (idx, file) in files.iter().enumerate() {
        let path = Path::new(file);
        if let Ok(ast) = parser::parse_file(path) {
            for node in &ast.nodes {
                if node.node_type.as_str() == "import" {
                    // Try to resolve the import to a file in our set
                    if let Some(target_idx) = resolve_import(&node.name, &file_set, file) {
                        graph.add_edge(idx, target_idx);
                    }
                }
            }
        }
    }

    graph
}

fn resolve_import(import_name: &str, file_set: &HashMap<&str, usize>, current_file: &str) -> Option<usize> {
    // Convert import name to potential file paths
    let module_path = import_name.replace('.', "/");
    let current_dir = Path::new(current_file).parent()?.to_string_lossy();

    let candidates = [
        format!("{}/{}.py", current_dir, module_path),
        format!("{}/{}/__init__.py", current_dir, module_path),
        format!("{}.py", module_path),
        format!("{}/__init__.py", module_path),
        format!("{}/{}.ts", current_dir, module_path),
        format!("{}.ts", module_path),
    ];

    for candidate in &candidates {
        if let Some(&idx) = file_set.get(candidate.as_str()) {
            return Some(idx);
        }
    }

    None
}

#[pyfunction]
pub fn py_walk_directory(root: String) -> Vec<String> {
    walk_directory(&root)
}

#[pyfunction]
pub fn py_build_dependency_graph(
    files: Vec<String>,
) -> (Vec<String>, Vec<(usize, usize)>, Vec<usize>) {
    let graph = build_dependency_graph(&files);
    let order = graph.topological_sort();
    (graph.nodes, graph.edges, order)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dependency_graph_topo_sort() {
        let mut graph = DependencyGraph::new();
        let a = graph.add_node("a.py".into());
        let b = graph.add_node("b.py".into());
        let c = graph.add_node("c.py".into());
        graph.add_edge(a, b);
        graph.add_edge(b, c);

        let order = graph.topological_sort();
        assert_eq!(order.len(), 3);
        // a should come before b, b before c
        let pos_a = order.iter().position(|&x| x == a).unwrap();
        let pos_b = order.iter().position(|&x| x == b).unwrap();
        let pos_c = order.iter().position(|&x| x == c).unwrap();
        assert!(pos_a < pos_b);
        assert!(pos_b < pos_c);
    }
}
