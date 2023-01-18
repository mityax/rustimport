// rustimport:pyo3

use pyo3::prelude::*;

#[pyfunction]
fn say_hello() -> String {
    "Hello from test_crate, implemented in Rust!".to_string()
}

// Uncomment the below to implement custom pyo3 binding code. Otherwise, 
// rustimport will generate it for you for all functions annotated with
// #[pyfunction] and all structs annotated with #[pyclass].
//
//#[pymodule]
//fn test_crate(_py: Python, m: &PyModule) -> PyResult<()> {
//    m.add_function(wrap_pyfunction!(say_hello, m)?)?;
//    Ok(())
//}
