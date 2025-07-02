mod iteration;

use bitgauss;
use pyo3::prelude::*;

/// Takes fault signatures of g1,g2 in normal form (stabilisers factored out) where the sink
/// containment information is provided in the last `..._sinks` elements of the signature.
///
/// Determines the smallest size of a combination `comb_sig` from elements of `g2_sig_nf` such that
/// - `comb_sig` does not enable any sinks and is thus not detectable AND EITHER
/// - `comb_sig` does not have an equivalent in `g1_sig_nf` (without sink information) OR
/// - the equivalent of `comb_sig` in `g1_sig_nf` has a greater size
///
/// :returns: the size of such a combination or `None` if no such combination exists.
#[pyfunction(name = "smallest_size_iteration")]
fn smallest_size_iteration_py(
    g1_sig_nf: Vec<Vec<bool>>,
    g2_sig_nf: Vec<Vec<bool>>,
    g1_sinks: usize,
    g2_sinks: usize,
) -> PyResult<Option<usize>> {
    let g1_sig_nf_r = g1_sig_nf
        .iter()
        .map(|sig| bitgauss::BitVec::from(sig.clone()))
        .collect::<Vec<_>>();
    let g2_sig_nf_r = g2_sig_nf
        .iter()
        .map(|sig| bitgauss::BitVec::from(sig.clone()))
        .collect::<Vec<_>>();

    Ok(iteration::smallest_size_iteration(
        g1_sig_nf_r,
        g2_sig_nf_r,
        g1_sinks,
        g2_sinks,
        false,
    ))
}

#[pymodule]
fn fault_signature(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(smallest_size_iteration_py, m)?)?;
    Ok(())
}
