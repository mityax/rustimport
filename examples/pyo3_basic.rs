// rustimport:pyo3

// Note: the above line tells rustimport to use the "pyo3" template, which will set up a minimal
// Cargo.toml file for our project when compiling and also generate the #[pymodule] macro
// automatically.

// Add the rand package to the Cargo.toml manifest.
//: [dependencies]
//: rand = "0.8.5"

use pyo3::prelude::*;
use rand::Rng;

/// Generates a random integer between `min` and `max`.
#[pyfunction]
fn random_number_from_rust(min: i32, max: i32) -> PyResult<i32> {
    Ok(rand::thread_rng().gen_range(min..max))
}

// Since we don't write a #[pymodule] macro here manually (see
// pyo3_manifest_only_templating.rs for an example), the "pyo3" template will automatically generate it for
// all functions annotated with #[pyfunction] and all structs annotated with #[pyclass].
