// rustimport

// Note: This file uses rustimport and pyo3, but it does not use rustimport's pyo3
// template, as it's not applied in the first line (compare to "// rustimport:pyo3").
// Thus, all configuration for cargo manifest and pyo3 needs to be supplied manually
// as below.

// This is our cargo manifest:

//: [package]
//: name = "singlefile"
//: version = "0.1.0"
//: edition = "2021"
//:
//: [lib]
//: # The name of the native library. This is the name which will be used in Python to import the
//: # library (i.e. `import string_sum`). If you change this, you must also change the name of the
//: # `#[pymodule]` below.
//: name = "singlefile"
//:
//: # Downstream Rust code (including code in `bin/`, `examples/`, and `examples/`) will not be able
//: # to `use singlefile;` unless the "rlib" or "lib" crate type is also included, e.g.:
//: # crate-type = ["cdylib", "rlib"]
//: crate-type = ["cdylib"]
//: # "cdylib" is necessary to produce a shared library for Python to import from.
//:
//: [dependencies]
//: pyo3 = { version = "0.16.2", features = ["extension-module"] }

use pyo3::prelude::*;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> String {
    (a + b).to_string()
}


// This is our pyo3 module definition.
// The name of this function must match the `lib.name` setting in the cargo manifest,
// else Python will not be able to import the module.
#[pymodule]
fn singlefile(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    Ok(())
}
