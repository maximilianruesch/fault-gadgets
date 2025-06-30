from typing import Optional, List, Mapping, Tuple

import numpy as np
from galois import GF2

from pyzx import VertexType
from pyzx.graph.base import upair
from pyzx.graph.graph_s import GraphS
from ...graph_helpers import add_sinks_for_all_detecting_regions
from ...gadget_web_fire import expand_all_gadgets
from ...graph import GadgetGraph
from ...web import compute_stabilisers, Pauli, PauliWeb
from .enumeration import _smallest_size_iteration
from .. import gadgets_to_signatures

ET = Tuple[int, int]

def _index_graph_boundaries(g: GraphS) -> Tuple[Mapping[ET, int], int]:
    boundaries_to_neighbors = { v: list(g.neighbors(v))[0] for v in g.vertices() if g.type(v) == VertexType.BOUNDARY }
    boundaries_to_idx = {}
    for i, b in enumerate(boundaries_to_neighbors.items()):
        if g.type(b[1]) == VertexType.BOUNDARY: # boundary <-> boundary
            boundaries_to_idx[b] = i
        else:
            boundaries_to_idx[upair(*b)] = i
    num_boundaries = len(boundaries_to_neighbors)

    return boundaries_to_idx, num_boundaries

def _index_graph_sinks(g: GadgetGraph) -> Tuple[Mapping[int, int], int]:
    sink_id_to_idx = { s: i for i, s in enumerate(g.sinks().keys()) }
    num_sinks = len(sink_id_to_idx)

    return sink_id_to_idx, num_sinks

def _stabiliser_rref(stabilisers: List[PauliWeb], num_boundaries: int, boundaries_to_idx: Mapping[ET, int]) -> GF2: # TODO get num_boundaries from index table
    np_stabilisers = np.zeros((len(stabilisers), num_boundaries * 2), dtype=int)
    for i, stab in enumerate(stabilisers):
        for edge, idx in boundaries_to_idx.items():
            if stab[edge] == Pauli.Z or stab[edge] == Pauli.Y: np_stabilisers[i, idx] = 1
            if stab[edge] == Pauli.X or stab[edge] == Pauli.Y: np_stabilisers[i, idx + num_boundaries] = 1

    return GF2(np_stabilisers).row_reduce(eye='left')

def _normalise_signature(sig: GF2, stabiliser_rref: GF2) -> GF2:
    normalised_sig = sig
    for stab in stabiliser_rref:
        largest_index = np.argmax(stab) # TODO precompute these for all stabilisers and reuse them (package stabilisers into their own cache)
        if stab[largest_index] == 1 and sig[largest_index] == 1:
            normalised_sig += stab
    return normalised_sig

def _calculate_signature_normal_forms(g: GadgetGraph, stabiliser_rref: GF2,
                                      boundaries_to_idx: Mapping[ET, int], num_boundaries: int,
                                      sink_id_to_idx: Mapping[int, int], num_sinks: int) -> List[GF2]:
    signatures = gadgets_to_signatures(g, g.gadgets().keys(), boundaries_to_idx, sink_id_to_idx)

    signature_normal_forms: List[GF2] = []
    for i, sig in enumerate(signatures.values()):
        np_sig = GF2.Zeros(num_boundaries * 2 + num_sinks)
        for j, pauli in enumerate(sig.boundaries):
            if pauli == Pauli.Z or pauli == Pauli.Y: np_sig[j] = 1
            if pauli == Pauli.X or pauli == Pauli.Y: np_sig[j + num_boundaries] = 1

        for k, active in enumerate(sig.sinks):
            if active: np_sig[k + num_boundaries * 2] = 1

        signature_normal_forms.append(_normalise_signature(np_sig, stabiliser_rref))

    return [GF2(l) for l in np.unique(signature_normal_forms, axis=0)]

def _add_gadgets(dg: GadgetGraph) -> None:
    for edge in list(dg.edges()):
        # Gadgets on inputs and outputs do not change for rewrites, thus skip
        if dg.type(edge[0]) is VertexType.BOUNDARY or dg.type(edge[1]) is VertexType.BOUNDARY:
            continue

        dg.add_edge_flip_gadgets(edge)

def _construct_signatures(g: GraphS, stabiliser_rref: GF2,
                          boundaries_to_idx: Mapping[ET, int], num_boundaries: int, quiet: bool = True) -> Tuple[GF2, List[GF2], int]:
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    sink_id_to_idx, num_sinks = _index_graph_sinks(gadget_graph)

    _add_gadgets(gadget_graph)
    expand_all_gadgets(gadget_graph, quiet=quiet)

    extended_stabiliser_rref = GF2(np.hstack([stabiliser_rref, GF2.Zeros((len(stabiliser_rref), num_sinks))]))
    sig_nf = _calculate_signature_normal_forms(gadget_graph, extended_stabiliser_rref,
                                               boundaries_to_idx, num_boundaries, sink_id_to_idx, num_sinks)

    return extended_stabiliser_rref, sig_nf, num_sinks

def _check_smallest_size(g1_stabiliser_rref: GF2, g1_sig_nf: List[GF2], g2_sig_nf: List[GF2],
                         g1_num_boundaries: int, g1_num_sinks: int, g2_num_sinks: int, quiet: bool = True) -> Optional[int]:
    augmented_g1_sig_nf = g1_sig_nf.copy()
    for i in range(g1_num_boundaries): # TODO remove non-unique elements
        # Z Signature
        x_atomic_sig = GF2.Zeros(g1_num_boundaries * 2 + g1_num_sinks)
        x_atomic_sig[i] = 1
        augmented_g1_sig_nf.append(_normalise_signature(x_atomic_sig, g1_stabiliser_rref))
        # X Signature
        z_atomic_sig = GF2.Zeros(g1_num_boundaries * 2 + g1_num_sinks)
        z_atomic_sig[i + g1_num_boundaries] = 1
        augmented_g1_sig_nf.append(_normalise_signature(z_atomic_sig, g1_stabiliser_rref))
        # Y Signature
        augmented_g1_sig_nf.append(_normalise_signature(x_atomic_sig + z_atomic_sig, g1_stabiliser_rref))

    return _smallest_size_iteration(augmented_g1_sig_nf, g2_sig_nf, g1_num_sinks, g2_num_sinks, quiet=quiet)

def is_distance_preserving(g1: GraphS, g2: GraphS, quiet: bool = True) -> bool:
    g1_boundaries_to_idx, g1_num_boundaries = _index_graph_boundaries(g1) # TODO index boundaries the same way / force the same inputs / outputs
    g2_boundaries_to_idx, g2_num_boundaries = _index_graph_boundaries(g2)
    if g1_num_boundaries != g2_num_boundaries:
        raise RuntimeError("Number of boundaries in graphs must be the same!")

    if not quiet: print("Computing stabilisers...")
    stabilisers = compute_stabilisers(g1) # TODO if strict, compute stabilisers of g2 and assert space equality
    stabiliser_rref = _stabiliser_rref(stabilisers, g1_num_boundaries, g1_boundaries_to_idx)

    if not quiet: print("Constructing signatures of g1...")
    g1_stabiliser_rref, g1_sig_nf, g1_num_sinks = _construct_signatures(g1, stabiliser_rref, g1_boundaries_to_idx, g1_num_boundaries, quiet=quiet)

    if not quiet: print("Constructing signatures of g2...")
    g2_stabiliser_rref, g2_sig_nf, g2_num_sinks = _construct_signatures(g2, stabiliser_rref, g2_boundaries_to_idx, g2_num_boundaries, quiet=quiet)

    if not quiet: print("Checking if g1 -> g2 is distance non-decreasing...")
    g1_g2_weight = _check_smallest_size(g1_stabiliser_rref, g1_sig_nf, g2_sig_nf, g1_num_boundaries, g1_num_sinks, g2_num_sinks, quiet=quiet)
    if g1_g2_weight is not None:
        return False

    if not quiet: print("Checking if g2 -> g1 is distance non-decreasing...")
    g2_g1_weight = _check_smallest_size(g2_stabiliser_rref, g2_sig_nf, g1_sig_nf, g2_num_boundaries, g2_num_sinks, g1_num_sinks, quiet=quiet)
    return g2_g1_weight is None
