pub mod bindings;
pub mod detector;
pub mod diff;
pub mod manifest;
pub mod parser;
pub mod pattern_engine;
pub mod validation;
pub mod walker;

use pyo3::prelude::*;

#[pymodule]
fn cloudshift_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    bindings::register(m)?;
    Ok(())
}
