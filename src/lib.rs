use pyo3::prelude::*;

mod fill_patterns;
mod polygon_utils;
mod vpype_interface;

use vpype_interface::{generate_fill_patterns, create_vpype_extension};

/// A Python module for generating fill patterns in polygons
#[pymodule]
fn vpype_cfill_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generate_fill_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(create_vpype_extension, m)?)?;
    Ok(())
}
