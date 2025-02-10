// rustimport:pyo3

// Instruct rustimport to track any changes in `test_crate` and rebuild this crate automatically:

//d: ../../test_crate/**/*.rs
//d: ../../test_crate/Cargo.toml

use pyo3::prelude::*;
use test_crate;


#[pyfunction]
fn say_hello() -> String {
    format!(
        "Hello from crate_relative_path_dependency, and also hello from test_crate: \"{}\"",
         test_crate::say_hello()
    )
}
