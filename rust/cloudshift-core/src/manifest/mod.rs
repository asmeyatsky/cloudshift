use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[pyclass(from_py_object)]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PyMigrationManifest {
    #[pyo3(get, set)]
    pub project_name: String,
    #[pyo3(get, set)]
    pub source_provider: String,
    #[pyo3(get, set)]
    pub target_provider: String,
    #[pyo3(get, set)]
    pub entries: Vec<PyManifestEntry>,
    #[pyo3(get, set)]
    pub total_files: usize,
    #[pyo3(get, set)]
    pub total_constructs: usize,
    #[pyo3(get, set)]
    pub overall_confidence: f64,
}

#[pymethods]
impl PyMigrationManifest {
    #[new]
    #[pyo3(signature = (project_name, source_provider="aws".to_string(), target_provider="gcp".to_string()))]
    pub fn new(
        project_name: String,
        source_provider: String,
        target_provider: String,
    ) -> Self {
        Self {
            project_name,
            source_provider,
            target_provider,
            entries: Vec::new(),
            total_files: 0,
            total_constructs: 0,
            overall_confidence: 0.0,
        }
    }

    pub fn add_entry(&mut self, entry: PyManifestEntry) {
        self.entries.push(entry);
        self.recalculate();
    }

    fn recalculate(&mut self) {
        self.total_constructs = self.entries.len();
        let files: std::collections::HashSet<&str> = self
            .entries
            .iter()
            .map(|e| e.file_path.as_str())
            .collect();
        self.total_files = files.len();

        if !self.entries.is_empty() {
            let sum: f64 = self.entries.iter().map(|e| e.confidence).sum();
            self.overall_confidence = sum / self.entries.len() as f64;
        }
    }

    pub fn to_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(self)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self) -> String {
        format!(
            "MigrationManifest(project='{}', {}->{}, files={}, constructs={}, confidence={:.2})",
            self.project_name,
            self.source_provider,
            self.target_provider,
            self.total_files,
            self.total_constructs,
            self.overall_confidence,
        )
    }
}

#[pyclass(from_py_object)]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PyManifestEntry {
    #[pyo3(get, set)]
    pub file_path: String,
    #[pyo3(get, set)]
    pub construct_type: String,
    #[pyo3(get, set)]
    pub source_service: String,
    #[pyo3(get, set)]
    pub target_service: String,
    #[pyo3(get, set)]
    pub source_text: String,
    #[pyo3(get, set)]
    pub target_text: String,
    #[pyo3(get, set)]
    pub pattern_id: String,
    #[pyo3(get, set)]
    pub confidence: f64,
    #[pyo3(get, set)]
    pub start_line: usize,
    #[pyo3(get, set)]
    pub end_line: usize,
    #[pyo3(get, set)]
    pub status: String,
    #[pyo3(get, set)]
    pub metadata: HashMap<String, String>,
}

#[pymethods]
impl PyManifestEntry {
    #[new]
    #[pyo3(signature = (file_path, construct_type, source_service, target_service, source_text, target_text="".to_string(), pattern_id="".to_string(), confidence=0.0, start_line=0, end_line=0, status="pending".to_string()))]
    pub fn new(
        file_path: String,
        construct_type: String,
        source_service: String,
        target_service: String,
        source_text: String,
        target_text: String,
        pattern_id: String,
        confidence: f64,
        start_line: usize,
        end_line: usize,
        status: String,
    ) -> Self {
        Self {
            file_path,
            construct_type,
            source_service,
            target_service,
            source_text,
            target_text,
            pattern_id,
            confidence,
            start_line,
            end_line,
            status,
            metadata: HashMap::new(),
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "ManifestEntry(file='{}', {}->{}, confidence={:.2}, status='{}')",
            self.file_path, self.source_service, self.target_service, self.confidence, self.status
        )
    }
}

#[pyfunction]
pub fn py_create_manifest(
    project_name: String,
    source_provider: String,
    target_provider: String,
) -> PyMigrationManifest {
    PyMigrationManifest::new(project_name, source_provider, target_provider)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_manifest() {
        let mut manifest =
            PyMigrationManifest::new("test-project".into(), "aws".into(), "gcp".into());
        assert_eq!(manifest.total_files, 0);
        assert_eq!(manifest.total_constructs, 0);

        manifest.add_entry(PyManifestEntry::new(
            "test.py".into(),
            "client_init".into(),
            "s3".into(),
            "gcs".into(),
            "boto3.client('s3')".into(),
            "storage.Client()".into(),
            "aws-s3-client-gcs".into(),
            0.90,
            3,
            3,
            "pending".into(),
        ));

        assert_eq!(manifest.total_files, 1);
        assert_eq!(manifest.total_constructs, 1);
        assert!((manifest.overall_confidence - 0.90).abs() < 0.001);
    }
}
