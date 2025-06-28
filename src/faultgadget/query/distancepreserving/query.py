import itertools
from functools import reduce
from typing import List, Tuple, Mapping

import numpy as np
from galois import GF2

from pyzx import VertexType
from pyzx.graph.base import upair
from pyzx.graph.graph_s import GraphS
from ...graph_helpers import add_sinks_for_all_detecting_regions
from ...gadget_web_fire import expand_all_gadgets
from ...graph import GadgetGraph
from ...web import Pauli, PauliWeb, compute_stabilisers
from .. import gadgets_to_signatures

ET = Tuple[int, int]

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

        for k, pauli in enumerate(sig.sinks):
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

def _sig_detectable(sig: GF2, sinks: int) -> int:
    return sinks > 0 and np.any(sig[-(sinks * 2):])

def _format_sig(sig: GF2, sinks: int) -> str:
    boundaries = (len(sig) - sinks * 2) // 2
    b_str = (f"{' '.join(map(str, sig[:boundaries]))}"
            f" | {' '.join(map(str, sig[boundaries:boundaries * 2]))}")
    if sinks == 0:
        return f"[{b_str}]"

    return (f"[{b_str}  ||  {' '.join(map(str, sig[boundaries * 2:boundaries * 2 + sinks]))}"
            f" | {' '.join(map(str, sig[boundaries * 2 + sinks:]))}]")

def _check_distance_non_decreasing(g1: GadgetGraph, g2: GadgetGraph, quiet: bool = True) -> bool:
    stabilisers = compute_stabilisers(g1)
    g1_num_sinks = len(g1.sinks())
    g2_num_sinks = len(g2.sinks())

    g1_normal_forms = _calculate_signature_normal_forms(g1, stabilisers)
    g2_normal_forms = _calculate_signature_normal_forms(g2, stabilisers)

    g1_lookup = dict() # TODO prepopulate with atomic output signatures if we do not add gadgets for them
    g2_lookup = dict()

    if not quiet: print(f"Starting weight iteration until {len(g2_normal_forms)}!")
    for max_weight in range(1, len(g2_normal_forms) + 1):
        if not quiet: print(f"Starting weight: {max_weight}...")
        # Populate g1_lookup for this weight
        for g1_sigs in itertools.combinations(g1_normal_forms, max_weight):
            combined_sig = reduce(lambda self, v: self + v, g1_sigs)
            if _sig_detectable(combined_sig, g1_num_sinks):
                continue # Detectable g1 signatures will never be queried, so save space here
            sig_int = _sig_wo_sinks_to_int(combined_sig, g1_num_sinks)
            if sig_int not in g1_lookup:
                g1_lookup[sig_int] = max_weight

        # Incrementally discover g2 signatures by combining `max_weight` signatures with weight = 1
        discovered_new = False
        for g2_sigs in itertools.combinations(g2_normal_forms, max_weight):
            combined_sig = reduce(lambda self, v: self + v, g2_sigs)
            sig_int = _sig_to_int(combined_sig)
            if sig_int == 0:
                continue # Trivial signature

            if sig_int in g2_lookup:
                continue # Already discovered

            discovered_new = True
            g2_lookup[sig_int] = max_weight
            if _sig_detectable(combined_sig, g2_num_sinks):
                continue # Detectable

            # Perform search with real output signature
            sig_int_wo_sinks = _sig_wo_sinks_to_int(combined_sig, g2_num_sinks)
            if sig_int_wo_sinks not in g1_lookup:
                if not quiet: print(f"{_format_sig(combined_sig, g2_num_sinks)} has no equivalent in g1!")
                return False # No equivalent error found

            if g1_lookup[sig_int_wo_sinks] > g2_lookup[sig_int]:
                if not quiet: print(f"{_format_sig(combined_sig, g2_num_sinks)} has higher weight in g1 ({g1_lookup[sig_int_wo_sinks]}) than in g2 ({g2_lookup[sig_int]})!")
                return False # Equivalent error has higher combinatory weight

        if False and not discovered_new:
            if not quiet: print("No new signatures discovered!")
            break

    return True

def _add_gadgets(dg: GadgetGraph) -> Mapping[ET, Tuple[int, int, int]]:
    edge_to_gadget_ids = dict()
    for edge in list(dg.edges()):
        # Gadgets on inputs and outputs do not change for rewrites, thus skip
        if dg.type(edge[0]) is VertexType.BOUNDARY or dg.type(edge[1]) is VertexType.BOUNDARY:
            continue

        edge_to_gadget_ids[edge] = dg.add_edge_flip_gadgets(edge)

    return edge_to_gadget_ids

def is_distance_preserving(g1: GraphS, g2: GraphS, quiet: bool = True) -> bool:
    if not quiet: print("Constructing signatures of g1...")
    gg1 = GadgetGraph.from_graph(g1)
    add_sinks_for_all_detecting_regions(gg1)
    _add_gadgets(gg1)
    expand_all_gadgets(gg1, quiet=quiet)

    if not quiet: print("Constructing signatures of g2...")
    gg2 = GadgetGraph.from_graph(g2)
    add_sinks_for_all_detecting_regions(gg2)

    _add_gadgets(gg2)
    expand_all_gadgets(gg2, quiet=quiet)

    if not quiet: print("Checking if g1 -> g2 is distance non-decreasing...")
    if not _check_distance_non_decreasing(gg1, gg2, quiet=quiet):
        return False

    if not quiet: print("Checking if g2 -> g1 is distance non-decreasing...")
    return _check_distance_non_decreasing(gg2, gg1, quiet=quiet)
