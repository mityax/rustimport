// rustimport:pyo3

use crate_b::sum;
use pyo3::prelude::*;

#[pyfunction]
fn double(x: i32) -> i32 {
    sum(x, x)
}
