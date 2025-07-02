use bitgauss;
use itertools::Itertools;
use std::collections::HashMap;

fn sig_to_int(sig: &bitgauss::BitVec) -> usize {
    let mut i = 0;
    for b in sig.iter() {
        i = (i << 1) | b as usize
    }
    i
}

fn sig_wo_sink_to_int(sig: &bitgauss::BitVec, sinks: usize) -> usize {
    let red_sig = if sinks > 0 {
        &sig.bit_range(sig.len() - sinks, sig.len()).to_vec()
    } else {
        sig
    };
    sig_to_int(red_sig)
}

fn is_sig_detectable(sig: &bitgauss::BitVec, sinks: usize) -> bool {
    sig.first_one_in_range(sig.len() - sinks, sig.len())
        .is_some()
}

fn format_sig(sig: &bitgauss::BitVec, sinks: usize) -> String {
    let boundaries = (sig.len() - sinks) / 2;
    let sig_str_1 = sig
        .bit_range(0, boundaries)
        .iter()
        .map(|b| b.to_string())
        .collect::<String>();
    let sig_str_2 = sig
        .bit_range(boundaries, boundaries * 2)
        .iter()
        .map(|b| b.to_string())
        .collect::<String>();
    let b_str = format!("{sig_str_1} | {sig_str_2}");
    if sinks == 0 {
        return b_str;
    }

    let s_str = sig
        .bit_range(boundaries * 2, sig.len())
        .iter()
        .map(|b| b.to_string())
        .collect::<String>();
    format!("{b_str}  ||  {s_str}")
}

pub fn smallest_size_iteration(
    g1_sig_nf: Vec<bitgauss::BitVec>,
    g2_sig_nf: Vec<bitgauss::BitVec>,
    g1_sinks: usize,
    g2_sinks: usize,
    quiet: bool,
) -> Option<usize> {
    let mut g1_lookup = HashMap::<usize, usize>::new();
    let mut g2_lookup = HashMap::<usize, usize>::new();

    if !quiet {
        println!("Starting iteration until {}", g2_sig_nf.len());
    }
    for max_size in 1..(g2_sig_nf.len() + 1) {
        if !quiet {
            println!("Starting iteration with combinatory size {max_size}");
        }
        // Populate g1_lookup for this weight
        for g1_sigs in g1_sig_nf.iter().combinations(max_size) {
            let mut combined_sig =
                bitgauss::BitVec::zeros(bitgauss::bitvec::min_blocks(g1_sigs[0].len()));
            g1_sigs.iter().for_each(|v| combined_sig.xor_in(v, 0));

            if is_sig_detectable(&combined_sig, g1_sinks) {
                continue;
            }

            let sig_int = sig_wo_sink_to_int(&combined_sig, g1_sinks);
            if !g1_lookup.contains_key(&sig_int) {
                g1_lookup.insert(sig_int, max_size);
            }
        }

        // Incrementally discover g2 signatures by combining #`max_size` atomic signatures
        let mut discovered_new = false;
        for g2_sigs in g2_sig_nf.iter().combinations(max_size) {
            let mut combined_sig =
                bitgauss::BitVec::zeros(bitgauss::bitvec::min_blocks(g2_sigs[0].len()));
            g2_sigs.iter().for_each(|v| combined_sig.xor_in(v, 0));
            let sig_int = sig_to_int(&combined_sig);
            if g1_lookup.contains_key(&sig_int) {
                continue;
            }

            if sig_int == 0 {
                continue;
            }

            discovered_new = true;
            g2_lookup.insert(sig_int, max_size);
            if is_sig_detectable(&combined_sig, g2_sinks) {
                continue;
            }

            if !g1_lookup.contains_key(&sig_wo_sink_to_int(&combined_sig, g2_sinks)) {
                if !quiet {
                    println!("{} has no equivalent in g1, or it was not yet generated and thus has higher weight!", format_sig(&combined_sig, g2_sinks));
                }
                return Some(max_size);
            }
        }

        if !discovered_new {
            if !quiet {
                println!("No new signatures discovered!");
            }
            break;
        }
    }

    None
}
