// rustimport:pyo3

use pyo3::prelude::*;


#[pyfunction]
fn say_hello() -> String {
    "Hello from declarative_module!".to_string()
}


// Manually define the Python module using pyO3's declarative module syntax:

#[pymodule]
mod declarative_module {
    #[pymodule_export]
    use super::say_hello; // Exports the `say_hello` function as part of the module
}
