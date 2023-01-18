use std::ops::Add;

// Generic method to build the sum of any to things that can be summed
pub fn sum<T: Add<Output = T>>(a: T, b: T) -> T {
    a + b
}
