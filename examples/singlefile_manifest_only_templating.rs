// rustimport:pyo3

// This is an example using rustimport's pyo3 template, but with manual pymodule
// configuration (see the end of this file). The template detects that and will
// only generate a cargo manifest for this file.

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn try_divide(a: usize, b: usize) -> PyResult<usize> {
    match b == 0 {
        false => Ok(a / b),
        true => Err(PyErr::new::<PyValueError, _>("Woops, that failed."))
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn singlefile_manifest_only_templating(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(try_divide, m)?)?;
    Ok(())
}
