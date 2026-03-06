mod catalogue;
mod matcher;
mod scorer;
mod transformer;

pub use catalogue::*;
pub use matcher::*;
pub use scorer::*;
pub use transformer::*;

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass(frozen, from_py_object)]
#[derive(Clone, Debug)]
pub struct PyTransformResult {
    #[pyo3(get)]
    pub pattern_id: String,
    #[pyo3(get)]
    pub original_text: String,
    #[pyo3(get)]
    pub transformed_text: String,
    #[pyo3(get)]
    pub import_additions: Vec<String>,
    #[pyo3(get)]
    pub import_removals: Vec<String>,
    #[pyo3(get)]
    pub confidence: f64,
    #[pyo3(get)]
    pub metadata: HashMap<String, String>,
}

#[pymethods]
impl PyTransformResult {
    fn __repr__(&self) -> String {
        format!(
            "TransformResult(pattern='{}', confidence={:.2})",
            self.pattern_id, self.confidence
        )
    }
}

impl From<TransformResult> for PyTransformResult {
    fn from(r: TransformResult) -> Self {
        PyTransformResult {
            pattern_id: r.pattern_id,
            original_text: r.original_text,
            transformed_text: r.transformed_text,
            import_additions: r.import_additions,
            import_removals: r.import_removals,
            confidence: r.confidence,
            metadata: r.metadata,
        }
    }
}

#[pyfunction]
pub fn py_load_patterns(patterns_dir: String) -> PyResult<usize> {
    let count = catalogue::load_patterns_from_dir(&patterns_dir)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    Ok(count)
}

#[pyfunction]
pub fn py_match_and_transform(
    node_type: String,
    node_name: String,
    node_text: String,
    provider: String,
    service: String,
    language: String,
    metadata: HashMap<String, String>,
) -> PyResult<Option<PyTransformResult>> {
    let construct = MatchConstruct {
        node_type,
        node_name,
        node_text: node_text.clone(),
        provider,
        service,
        language,
        metadata,
    };

    let catalogue = GLOBAL_CATALOGUE.read().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to read catalogue: {}", e))
    })?;

    if let Some(rule) = matcher::find_best_match(&catalogue, &construct) {
        let result = transformer::apply_rule(rule, &node_text);
        Ok(Some(result.into()))
    } else {
        Ok(None)
    }
}
