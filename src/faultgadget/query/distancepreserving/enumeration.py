import itertools
from functools import reduce
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

def _is_sig_detectable(sig: GF2, sinks: int) -> int:
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

    if not quiet: print(f"Starting iteration until {len(g2_sig_nf)}!")
    for max_size in range(1, len(g2_sig_nf) + 1):
        if not quiet: print(f"Starting iteration with combinatory size: {max_size}...")
        # Populate g1_lookup for this weight
        for g1_sigs in itertools.combinations(g1_sig_nf, max_size):
            combined_sig = reduce(lambda self, v: self + v, g1_sigs)
            if _is_sig_detectable(combined_sig, g1_sinks):
                continue # Detectable g1 signatures will never be queried, save space here

            sig_int = _sig_wo_sinks_to_int(combined_sig, g1_sinks)
            if sig_int not in g1_lookup:
                g1_lookup[sig_int] = max_size

        # Incrementally discover g2 signatures by combining #`max_size` atomic signatures
        discovered_new = False
        for g2_sigs in itertools.combinations(g2_sig_nf, max_size):
            combined_sig = reduce(lambda self, v: self + v, g2_sigs)
            sig_int = _sig_to_int(combined_sig)
            if sig_int == 0:
                continue # Trivial signature

            if sig_int in g2_lookup:
                continue # Already discovered

            discovered_new = True
            g2_lookup[sig_int] = max_size
            if _is_sig_detectable(combined_sig, g2_sinks):
                continue # Detectable

            # Perform search with real output signature
            if _sig_wo_sinks_to_int(combined_sig, g2_sinks) not in g1_lookup:
                if not quiet: print(f"{_format_sig(combined_sig, g2_sinks)} has no equivalent in g1, or it was not yet generated and thus has higher weight!")
                return max_size # No equivalent error with equal or lower weight found

        if not discovered_new:
            if not quiet: print("No new signatures discovered!")
            break

    return None
