// rustimport:pyo3

//: [dependencies]
//: test_crate = { path = "./test_crate" }

use pyo3::prelude::*;
use test_crate;

#[pyfunction]
fn say_hello() -> String {
    format!(
        "Hello from singlefile_relative_path_dependency, and also hello from test_crate: \"{}\"",
         test_crate::say_hello()
    )
}
