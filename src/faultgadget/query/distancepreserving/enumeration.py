import itertools
from tqdm.auto import tqdm
import time
from typing import List, Optional

import numpy as np
from galois import GF2

def _sig_to_int(sig: GF2) -> int:
    out = 0
    for bit in sig.tolist():
        out = (out << 1) | bit
    return out

def _sig_wo_sinks_to_int(sig: GF2, sinks: int) -> int:
    reduced_sig = sig[:-sinks] if sinks > 0 else sig
    return _sig_to_int(reduced_sig)

def _is_sig_detectable(sig: GF2, sinks: int) -> bool:
    return sinks > 0 and np.any(sig[-sinks:])

def _format_sig(sig: GF2, sinks: int) -> str:
    boundaries = (len(sig) - sinks) // 2
    b_str = (f"{' '.join(map(str, sig[:boundaries]))}"
            f" | {' '.join(map(str, sig[boundaries:boundaries * 2]))}")
    if sinks == 0:
        return f"[{b_str}]"

    return f"[{b_str}  ||  {' '.join(map(str, sig[boundaries * 2:]))}]"

def _smallest_size_iteration(g1_sig_nf: List[GF2], g2_sig_nf: List[GF2],
                             g1_sinks: int, g2_sinks: int, quiet: bool = True) -> Optional[int]:
    """
    Takes fault signatures of g1,g2 in normal form (stabilisers factored out) where the sink containment information is
    provided in the last `..._sinks` elements of the signature.

    Determines the smallest size of a combination `comb_sig` from elements of `g2_sig_nf` such that

    - `comb_sig` does not enable any sinks and is thus not detectable AND EITHER
    - `comb_sig` does not have an equivalent in `g1_sig_nf` (without sink information) OR
    - the equivalent of `comb_sig` in `g1_sig_nf` has a greater size

    :returns: the size of such a combination or `None` if no such combination exists.
    """

    g1_lookup = dict()
    g2_lookup = dict()

    if len(g2_sig_nf) == 0:
        if not quiet: print("No signatures to match for g2!")
        return None
    num_max_signatures = 2 ** ((len(g2_sig_nf[0]) - g2_sinks) // 2 + g2_sinks)
    num_total_signatures = 0

    if not quiet: print(f"Starting iteration until {len(g2_sig_nf)}!")
    g1_last_new_signatures = [GF2.Zeros(g1_sig_nf[0].shape)]
    g2_last_new_detectable = [GF2.Zeros(g2_sig_nf[0].shape)]
    for max_size in tqdm(range(1, len(g2_sig_nf) + 1),
                        desc='Weight: ', initial=1, total=len(g2_sig_nf), leave=False, disable=quiet):
        if not quiet: tqdm.write(f"Starting iteration with combinatory size: {max_size}...")
        # Populate g1_lookup for this weight
        g1_time = time.time()
        g1_new_signatures = []
        for last_it, atomic_sig_nf in itertools.product(g1_last_new_signatures, g1_sig_nf):
            combined_sig = last_it + atomic_sig_nf
            if _is_sig_detectable(combined_sig, g1_sinks):
                continue # Detectable g1 signatures will never be queried, save space here

            sig_int = _sig_wo_sinks_to_int(combined_sig, g1_sinks)
            if sig_int not in g1_lookup:
                g1_new_signatures.append(combined_sig)
                g1_lookup[sig_int] = max_size
        g1_last_new_signatures = g1_new_signatures
        if not quiet: tqdm.write(f"Populating g1 lookup took {time.time() - g1_time}s.")

        # Incrementally discover g2 signatures by combining #`max_size` atomic signatures
        g2_time = time.time()
        num_new_signatures = 0
        g2_new_detectable = []
        for last_it, atomic_sig_nf in tqdm(itertools.product(g2_last_new_detectable, g2_sig_nf),
                                        desc='Signatures: ', total=len(g2_last_new_detectable) * len(g2_sig_nf),
                                        leave=False, disable=quiet):
            combined_sig = last_it + atomic_sig_nf
            sig_int = _sig_to_int(combined_sig)
            if sig_int in g2_lookup:
                continue # Already discovered

            num_new_signatures += 1
            g2_lookup[sig_int] = max_size
            if _is_sig_detectable(combined_sig, g2_sinks):
                g2_new_detectable.append(combined_sig)
                continue # Detectable

            # Perform search with real output signature
            if _sig_wo_sinks_to_int(combined_sig, g2_sinks) not in g1_lookup:
                if not quiet: tqdm.write(f"{_format_sig(combined_sig, g2_sinks)} has no equivalent in g1, or it was not yet generated and thus has higher weight!")
                return max_size # No equivalent error with equal or lower weight found
        if not quiet: tqdm.write(f"Populating g2 lookup took {time.time() - g2_time}s.")

        g2_last_new_detectable = g2_new_detectable
        num_total_signatures += num_new_signatures
        if num_new_signatures == 0:
            if not quiet: tqdm.write("No new signatures discovered!")
            break
        else:
            if not quiet: tqdm.write(f"Discovered {num_new_signatures} new signatures this iteration (so far: {num_total_signatures}, max signatures: {num_max_signatures})!.")

    return None
