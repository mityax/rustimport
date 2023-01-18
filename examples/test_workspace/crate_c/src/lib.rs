// rustimport:pyo3

use pyo3::prelude::*;

use crate_b::sum;

#[pyfunction]
fn fibanocci(n: usize) -> Vec<i128> {
    let mut res = Vec::with_capacity(n);

    for _ in 0..n {
        res.push(match res.len() {
            0 => 1,
            1 => 1,
            l => sum(res[l - 2], res[l - 1])
        });
    }

    res
}
