use pyo3::prelude::*;

use crate::detector;
use crate::diff;
use crate::manifest;
use crate::parser;
use crate::pattern_engine;
use crate::validation;
use crate::walker;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parser::py_parse_file, m)?)?;
    m.add_function(wrap_pyfunction!(parser::py_parse_source, m)?)?;
    m.add_function(wrap_pyfunction!(detector::py_detect_services, m)?)?;
    m.add_function(wrap_pyfunction!(
        pattern_engine::py_match_and_transform,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(pattern_engine::py_load_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(diff::py_unified_diff, m)?)?;
    m.add_function(wrap_pyfunction!(diff::py_ast_diff, m)?)?;
    m.add_function(wrap_pyfunction!(walker::py_walk_directory, m)?)?;
    m.add_function(wrap_pyfunction!(walker::py_build_dependency_graph, m)?)?;
    m.add_function(wrap_pyfunction!(
        validation::py_check_ast_equivalence,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(validation::py_scan_residual_refs, m)?)?;
    m.add_function(wrap_pyfunction!(manifest::py_create_manifest, m)?)?;

    m.add_class::<manifest::PyMigrationManifest>()?;
    m.add_class::<manifest::PyManifestEntry>()?;
    m.add_class::<parser::PyFileAst>()?;
    m.add_class::<parser::PyAstNode>()?;
    m.add_class::<detector::PyServiceDetection>()?;
    m.add_class::<pattern_engine::PyTransformResult>()?;
    m.add_class::<validation::PyValidationResult>()?;

    Ok(())
}
