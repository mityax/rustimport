// rustimport:pyo3

// Below, we specify a dependency on a path relative to the current file. Since rustimport builds
// your extensions in a temporary location, it will automatically rewrite this path and turn it
// into an absolute one:

//: [dependencies]
//: test_crate = { path = "./test_crate" }

// If you also want rustimport to automatically rebuild this extension when anything in `test_crate`
// is changed, you can specify dependency paths like below:

//d: ./test_crate/Cargo.toml
//d: ./test_crate/**/*.rs



use pyo3::prelude::*;
use test_crate;

#[pyfunction]
fn say_hello() -> String {
    format!(
        "Hello from relative_path_dependency.rs, and also hello from test_crate: \"{}\"",
         test_crate::say_hello()
    )
}
