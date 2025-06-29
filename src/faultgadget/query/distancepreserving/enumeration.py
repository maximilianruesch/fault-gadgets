import itertools
from functools import reduce
from typing import List, Optional

import numpy as np
from galois import GF2

from pyzx import VertexType
from pyzx.graph.base import upair
from ...graph import GadgetGraph
from ...web import Pauli, PauliWeb
from .. import gadgets_to_signatures

def _calculate_signature_normal_forms(g: GadgetGraph, stabilisers: List[PauliWeb]) -> List[GF2]:
    boundaries_to_neighbors = { v: list(g.neighbors(v))[0] for v in g.vertices() if g.type(v) == VertexType.BOUNDARY }
    boundaries_to_idx = {} # TODO index boundaries the same way / force the same inputs / outputs
    for i, b in enumerate(boundaries_to_neighbors.items()):
        if g.type(b[1]) == VertexType.BOUNDARY: # boundary <-> boundary
            boundaries_to_idx[b] = i
        else:
            boundaries_to_idx[upair(*b)] = i
    num_boundaries = len(boundaries_to_neighbors)

    sink_id_to_idx = { s: i for i, s in enumerate(g.sinks().keys()) }
    num_sinks = len(sink_id_to_idx)

    signatures = gadgets_to_signatures(g, g.gadgets().keys(), boundaries_to_idx, sink_id_to_idx)

    num_escapes = num_boundaries + num_sinks

    np_stabilisers = np.zeros((len(stabilisers), num_escapes * 2), dtype=int)
    for i, stab in enumerate(stabilisers):
        for edge, idx in boundaries_to_idx.items():
            if stab[edge] == Pauli.Z or stab[edge] == Pauli.Y: np_stabilisers[i, idx] = 1
            if stab[edge] == Pauli.X or stab[edge] == Pauli.Y: np_stabilisers[i, idx + num_boundaries] = 1
    stabiliser_rref = GF2(np_stabilisers).row_reduce(eye='left')

    signature_normal_forms: List[GF2] = []
    for i, sig in enumerate(signatures.values()):
        np_sig = GF2.Zeros(num_escapes * 2)
        for j, pauli in enumerate(sig.boundaries):
            if pauli == Pauli.Z or pauli == Pauli.Y: np_sig[j] = 1
            if pauli == Pauli.X or pauli == Pauli.Y: np_sig[j + num_boundaries] = 1

        for k, pauli in enumerate(sig.sinks): # TODO reduce sink information size
            if pauli == Pauli.Z or pauli == Pauli.Y: np_sig[k + num_boundaries * 2] = 1
            if pauli == Pauli.X or pauli == Pauli.Y: np_sig[k + num_boundaries * 2 + num_sinks] = 1

        for l in range(len(stabilisers)):
            if np_sig[l] == 1:
                np_sig += stabiliser_rref[l]
        signature_normal_forms.append(np_sig)

    return np.unique(GF2(signature_normal_forms), axis=0).view(GF2)

def _sig_to_int(sig: GF2) -> int:
    out = 0
    for bit in sig.tolist():
        out = (out << 1) | bit
    return out

def _sig_wo_sinks_to_int(sig: GF2, sinks: int) -> int:
    reduced_sig = sig[:-(sinks * 2)] if sinks > 0 else sig
    return _sig_to_int(reduced_sig)

def _is_sig_detectable(sig: GF2, sinks: int) -> int:
    return sinks > 0 and np.any(sig[-(sinks * 2):])

def _format_sig(sig: GF2, sinks: int) -> str:
    boundaries = (len(sig) - sinks * 2) // 2
    b_str = (f"{' '.join(map(str, sig[:boundaries]))}"
            f" | {' '.join(map(str, sig[boundaries:boundaries * 2]))}")
    if sinks == 0:
        return f"[{b_str}]"

    return (f"[{b_str}  ||  {' '.join(map(str, sig[boundaries * 2:boundaries * 2 + sinks]))}"
            f" | {' '.join(map(str, sig[boundaries * 2 + sinks:]))}]")

def _smallest_size_iteration(g1_sig_nf: List[GF2], g2_sig_nf: List[GF2],
                             g1_sinks: int, g2_sinks: int, quiet: bool = True) -> Optional[int]:
    """
    Takes fault signatures of g1,g2 in normal form (stabilisers factored out) where the sink containment information is
    provided in the last `..._sinks * 2` elements of the signature.

    Determines the smallest size of a combination `comb_sig` from elements of `g2_sig_nf` such that

    - `comb_sig` does not enable any sinks and is thus not detectable AND EITHER
    - `comb_sig` does not have an equivalent in `g1_sig_nf` (without sink information) OR
    - the equivalent of `comb_sig` in `g1_sig_nf` has a greater size

    :returns: the size of such a combination or `None` if no such combination exists.
    """

    g1_lookup = dict() # TODO prepopulate with atomic output signatures if we do not add gadgets for them
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
            sig_int_wo_sinks = _sig_wo_sinks_to_int(combined_sig, g2_sinks)
            if sig_int_wo_sinks not in g1_lookup:
                if not quiet: print(f"{_format_sig(combined_sig, g2_sinks)} has no equivalent in g1!")
                return max_size # No equivalent error found

            if g1_lookup[sig_int_wo_sinks] > g2_lookup[sig_int]:
                if not quiet: print(f"{_format_sig(combined_sig, g2_sinks)} has higher weight in g1 ({g1_lookup[sig_int_wo_sinks]}) than in g2 ({g2_lookup[sig_int]})!")
                return max_size # Equivalent error has higher combinatory weight

        if False and not discovered_new:
            if not quiet: print("No new signatures discovered!")
            break

    return None
