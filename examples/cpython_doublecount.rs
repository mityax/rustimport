// rustimport

// Here, we use `rust-cpython` instead of pyO3:
//  - Notice how we do not have "rustimport:pyo3" in the first line of this
//    file (-> we don't activate the pyO3 template)
//  - Below, you find the full manifest (Cargo.toml) definition, which is usually
//    automatically defined by pyO3

//: [package]
//: name = "cpython_doublecount"
//: version = "0.1.0"
//: authors = ["Bruno Rocha <rochacbruno@gmail.com>"]
//:
//: [lib]
//: name = "cpython_doublecount"
//: crate-type = ["cdylib"]
//:
//: [dependencies.cpython]
//: version = "0.7"
//: features = ["extension-module"]

#[macro_use]
extern crate cpython;

use cpython::{Python, PyResult};

fn count_doubles(_py: Python, val: &str) -> PyResult<u64> {
    let mut total = 0u64;

    let mut chars = val.chars();
    if let Some(mut c1) = chars.next() {
        for c2 in chars {
            if c1 == c2 {
                total += 1;
            }
            c1 = c2;
        }
    }

    Ok(total)
}

py_module_initializer!(cpython_doublecount, |py, m | {
    m.add(py, "__doc__", "This module is implemented in Rust.")?;
    m.add(py, "count_doubles", py_fn!(py, count_doubles(val: &str)))?;
    Ok(())
});
