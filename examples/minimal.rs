// rustimport:pyo3

use pyo3::prelude::*;

#[pyfunction]
fn say_hello() -> String {
    "Hello from Rust!".to_string()
}