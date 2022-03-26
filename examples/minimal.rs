// rustimport:pyo3

use pyo3::prelude::*;

#[pyfunction]
fn say_hello() {
    println!("Hello from Rust!")
}