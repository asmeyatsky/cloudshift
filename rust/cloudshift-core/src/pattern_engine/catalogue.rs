use std::collections::HashMap;
use std::path::Path;
use std::sync::RwLock;

use serde::Deserialize;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CatalogueError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("YAML parse error: {0}")]
    Yaml(#[from] serde_yaml::Error),
    #[error("Invalid pattern: {0}")]
    InvalidPattern(String),
}

#[derive(Debug, Clone, Deserialize)]
pub struct PatternRule {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub description: String,
    pub source_provider: String,
    pub target_provider: String,
    pub source_service: String,
    pub target_service: String,
    pub language: String,
    #[serde(default)]
    pub construct_type: String,
    pub match_pattern: MatchPattern,
    pub transform: TransformSpec,
    #[serde(default = "default_confidence")]
    pub base_confidence: f64,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub examples: Vec<PatternExample>,
}

fn default_confidence() -> f64 {
    0.80
}

#[derive(Debug, Clone, Deserialize)]
pub struct MatchPattern {
    #[serde(default)]
    pub imports: Vec<String>,
    #[serde(default)]
    pub client_names: Vec<String>,
    #[serde(default)]
    pub method_names: Vec<String>,
    #[serde(default)]
    pub resource_types: Vec<String>,
    #[serde(default)]
    pub text_patterns: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TransformSpec {
    pub replacement_template: String,
    #[serde(default)]
    pub import_additions: Vec<String>,
    #[serde(default)]
    pub import_removals: Vec<String>,
    #[serde(default)]
    pub notes: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PatternExample {
    pub input: String,
    pub output: String,
}

#[derive(Debug, Default)]
pub struct RuleCatalogue {
    pub rules: Vec<PatternRule>,
    pub by_service: HashMap<String, Vec<usize>>,
    pub by_language: HashMap<String, Vec<usize>>,
    pub by_provider: HashMap<String, Vec<usize>>,
}

impl RuleCatalogue {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_rule(&mut self, rule: PatternRule) {
        let idx = self.rules.len();
        self.by_service
            .entry(rule.source_service.clone())
            .or_default()
            .push(idx);
        self.by_language
            .entry(rule.language.clone())
            .or_default()
            .push(idx);
        self.by_provider
            .entry(rule.source_provider.clone())
            .or_default()
            .push(idx);
        self.rules.push(rule);
    }

    pub fn len(&self) -> usize {
        self.rules.len()
    }

    pub fn is_empty(&self) -> bool {
        self.rules.is_empty()
    }
}

pub static GLOBAL_CATALOGUE: std::sync::LazyLock<RwLock<RuleCatalogue>> =
    std::sync::LazyLock::new(|| RwLock::new(RuleCatalogue::new()));

pub fn load_patterns_from_dir(dir: &str) -> Result<usize, CatalogueError> {
    let path = Path::new(dir);
    let mut catalogue = GLOBAL_CATALOGUE.write().map_err(|_| {
        CatalogueError::InvalidPattern("Failed to acquire write lock".into())
    })?;

    let mut count = 0;

    if !path.exists() {
        return Ok(0);
    }

    fn walk_yaml(dir: &Path, catalogue: &mut RuleCatalogue, count: &mut usize) -> Result<(), CatalogueError> {
        if dir.is_dir() {
            for entry in std::fs::read_dir(dir)? {
                let entry = entry?;
                let path = entry.path();
                if path.is_dir() {
                    walk_yaml(&path, catalogue, count)?;
                } else if path.extension().is_some_and(|e| e == "yaml" || e == "yml") {
                    // Skip the schema file
                    if path.file_name().is_some_and(|n| n == "schema.yaml") {
                        continue;
                    }
                    let content = std::fs::read_to_string(&path)?;
                    // A YAML file may contain multiple patterns (using --- separator)
                    for doc in serde_yaml::Deserializer::from_str(&content) {
                        match PatternRule::deserialize(doc) {
                            Ok(rule) => {
                                catalogue.add_rule(rule);
                                *count += 1;
                            }
                            Err(e) => {
                                eprintln!("Warning: failed to parse pattern in {:?}: {}", path, e);
                            }
                        }
                    }
                }
            }
        }
        Ok(())
    }

    walk_yaml(path, &mut catalogue, &mut count)?;
    Ok(count)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_catalogue_new() {
        let cat = RuleCatalogue::new();
        assert!(cat.is_empty());
    }

    #[test]
    fn test_add_rule() {
        let mut cat = RuleCatalogue::new();
        cat.add_rule(PatternRule {
            id: "test-001".into(),
            name: "Test Rule".into(),
            description: String::new(),
            source_provider: "aws".into(),
            target_provider: "gcp".into(),
            source_service: "s3".into(),
            target_service: "gcs".into(),
            language: "python".into(),
            construct_type: "client_init".into(),
            match_pattern: MatchPattern {
                imports: vec!["boto3".into()],
                client_names: vec!["boto3.client".into()],
                method_names: vec![],
                resource_types: vec![],
                text_patterns: vec![],
            },
            transform: TransformSpec {
                replacement_template: "storage.Client()".into(),
                import_additions: vec!["from google.cloud import storage".into()],
                import_removals: vec!["import boto3".into()],
                notes: String::new(),
            },
            base_confidence: 0.90,
            tags: vec!["storage".into()],
            examples: vec![],
        });
        assert_eq!(cat.len(), 1);
        assert_eq!(cat.by_service["s3"].len(), 1);
    }
}
