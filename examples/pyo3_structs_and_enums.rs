// rustimport:pyo3

use pyo3::prelude::*;

// Define simple structs like this:

#[pyclass]
struct MyStruct {
    my_value: i8,
}


// Structs can be more complex, for example they can use other macros:

#[pyclass(eq)]  // make this struct equatable using pyo3's helpers...
#[derive(PartialEq)]  // ... and also implement equatability on the rust side using `PartialEq`
/* #[derive(Debug)] */
pub struct MyOtherStruct {
    my_value: i8,
}


// And of course they can have implementations:

#[pymethods]
impl MyOtherStruct {
    #[new]
    fn new(value: i8) -> Self {
        MyOtherStruct {
            my_value: value
        }
    }

    fn get_doubled_value(&self) -> i8 {
        self.my_value * 2
    }
}


// Enums are supported too:

#[pyclass(eq, eq_int)]
#[derive(PartialEq)]
enum MyEnum {
    A,
    B,
    C = 42,
}


// ... and can be more complex:

#[pyclass(eq)]
#[derive(PartialEq)]
enum MyOtherEnum {
    A(),
    B { value: i8 },
    C(String),
}

