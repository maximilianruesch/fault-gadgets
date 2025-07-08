from typing import List, Mapping, Tuple

import numpy as np
from galois import GF2

from pyzx import VertexType
from pyzx.graph.graph_s import GraphS
from ...gadget_web_compute import compute_signatures_for_gadgets
from ...graph_helpers import add_sinks_for_all_detecting_regions
from ...graph import GadgetGraph
from ...web import compute_stabilisers, Pauli, PauliWeb
from .enumeration import _smallest_size_iteration
from ... import Signature

ET = Tuple[int, int]

def _index_graph_boundaries(g: GraphS) -> Tuple[Mapping[int, int], int]:
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    return { b: i for i, b in enumerate(boundaries)}, len(boundaries)

def _index_graph_sinks(g: GadgetGraph) -> Tuple[Mapping[int, int], int]:
    sink_id_to_idx = { s: i for i, s in enumerate(g.sinks().keys()) }
    num_sinks = len(sink_id_to_idx)

    return sink_id_to_idx, num_sinks

class AugmentedStabilisers:
    def __init__(self, stabiliser_rref: GF2, num_sinks: int):
        self._rref = GF2(np.hstack([stabiliser_rref, GF2.Zeros((len(stabiliser_rref), num_sinks))]))
        self._indices = np.argmax(self._rref, axis=1).view(np.ndarray)

    def normalise_signature(self, sig: GF2) -> GF2:
        normalised_sig = sig
        for stab, idx in zip(self._rref, self._indices):
            if stab[idx] == 1 and sig[idx] == 1:
                normalised_sig += stab
        return normalised_sig

def _stabiliser_rref(stabilisers: List[PauliWeb], boundaries_to_idx: Mapping[int, int]) -> GF2:
    num_boundaries = len(boundaries_to_idx)
    np_stabilisers = np.zeros((len(stabilisers), num_boundaries * 2), dtype=int)
    for i, stab in enumerate(stabilisers):
        for boundary, idx in boundaries_to_idx.items():
            paulis = [p for e, p in stab.half_edges().items() if e[0] == boundary]
            assert len(paulis) <= 1
            pauli = paulis[0] if len(paulis) == 1 else None
            if pauli == Pauli.Z or pauli == Pauli.Y: np_stabilisers[i, idx] = 1
            if pauli == Pauli.X or pauli == Pauli.Y: np_stabilisers[i, idx + num_boundaries] = 1

    return GF2(np_stabilisers).row_reduce(eye='left')

def _calculate_signature_normal_forms(signatures: Mapping[int, Signature], stabs: AugmentedStabilisers,
                                      boundaries_to_idx: Mapping[int, int], num_boundaries: int,
                                      sink_to_idx: Mapping[int, int], num_sinks: int) -> List[GF2]:
    signature_normal_forms: List[GF2] = []
    for i, sig in enumerate(signatures.values()):
        np_sig = GF2.Zeros(num_boundaries * 2 + num_sinks)
        for boundary, pauli in sig.boundaries.items():
            idx = boundaries_to_idx[boundary]
            if pauli == Pauli.Z or pauli == Pauli.Y: np_sig[idx] = 1
            if pauli == Pauli.X or pauli == Pauli.Y: np_sig[idx + num_boundaries] = 1

        for sink, active in sig.sinks.items():
            if active: np_sig[sink_to_idx[sink] + num_boundaries * 2] = 1

        signature_normal_forms.append(stabs.normalise_signature(np_sig))

    return [GF2(l) for l in np.unique(signature_normal_forms, axis=0)]

def _add_gadgets(dg: GadgetGraph) -> None:
    for edge in list(dg.edges()):
        # Gadgets on inputs and outputs do not change for rewrites, thus skip
        if dg.type(edge[0]) is VertexType.BOUNDARY or dg.type(edge[1]) is VertexType.BOUNDARY:
            continue

        dg.add_edge_flip_gadgets(edge)

def _construct_signatures(g: GraphS, stabiliser_rref: GF2, boundaries_to_idx: Mapping[int, int],
                          num_boundaries: int) -> Tuple[AugmentedStabilisers, List[GF2], int]:
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    sink_id_to_idx, num_sinks = _index_graph_sinks(gadget_graph)

    _add_gadgets(gadget_graph)
    signatures = compute_signatures_for_gadgets(gadget_graph, gadget_graph.gadgets().keys())
    # Remove trivial signatures # TODO remove once somewhere...
    signatures = {_id: signature for _id, signature in signatures.items() if len(signature.boundaries) > 0 or len(signature.sinks) > 0}

    stabs = AugmentedStabilisers(stabiliser_rref, num_sinks)
    sig_nf = _calculate_signature_normal_forms(signatures, stabs, boundaries_to_idx, num_boundaries, sink_id_to_idx, num_sinks)

    return stabs, sig_nf, num_sinks

def _add_boundary_signatures(stabs: AugmentedStabilisers, sig_nf: List[GF2], num_boundaries: int, num_sinks: int) -> List[GF2]:
    augmented_sig_nf = sig_nf.copy()
    for i in range(num_boundaries): # TODO remove non-unique elements
        # Z Signature
        x_atomic_sig = GF2.Zeros(num_boundaries * 2 + num_sinks)
        x_atomic_sig[i] = 1
        augmented_sig_nf.append(stabs.normalise_signature(x_atomic_sig))
        # X Signature
        z_atomic_sig = GF2.Zeros(num_boundaries * 2 + num_sinks)
        z_atomic_sig[i + num_boundaries] = 1
        augmented_sig_nf.append(stabs.normalise_signature(z_atomic_sig))
        # Y Signature
        augmented_sig_nf.append(stabs.normalise_signature(x_atomic_sig + z_atomic_sig))

    return augmented_sig_nf

def is_fault_equivalent(g1: GraphS, g2: GraphS, quiet: bool = True) -> bool:
    """
    Given two diagrams g1 and g2, determine if they are fault equivalent under the edge flip noise model.
    """
    g1_boundaries_to_idx, g1_num_boundaries = _index_graph_boundaries(g1) # TODO index boundaries the same way / force the same inputs / outputs
    g2_boundaries_to_idx, g2_num_boundaries = _index_graph_boundaries(g2)
    if g1_num_boundaries != g2_num_boundaries:
        raise RuntimeError("Number of boundaries in graphs must be the same!")

    if not quiet: print("Computing stabilisers...")
    stabilisers = compute_stabilisers(g1) # TODO if strict, compute stabilisers of g2 and assert space equality
    stabiliser_rref = _stabiliser_rref(stabilisers, g1_boundaries_to_idx)

    if not quiet: print("Constructing signatures of g1...")
    g1_stabs, g1_sig_nf, g1_num_sinks = _construct_signatures(g1, stabiliser_rref, g1_boundaries_to_idx, g1_num_boundaries)

    if not quiet: print("Constructing signatures of g2...")
    g2_stabs, g2_sig_nf, g2_num_sinks = _construct_signatures(g2, stabiliser_rref, g2_boundaries_to_idx, g2_num_boundaries)

    if not quiet: print("Checking if g1 -> g2 is fault bounded...")
    augmented_g1_sig_nf = _add_boundary_signatures(g1_stabs, g1_sig_nf, g1_num_boundaries, g1_num_sinks)
    g1_g2_weight = _smallest_size_iteration(augmented_g1_sig_nf, g2_sig_nf, g1_num_sinks, g2_num_boundaries, g2_num_sinks, quiet=quiet)
    if g1_g2_weight is not None:
        return False

    if not quiet: print("Checking if g2 -> g1 is fault bounded...")
    augmented_g2_sig_nf = _add_boundary_signatures(g2_stabs, g2_sig_nf, g2_num_boundaries, g2_num_sinks)
    g2_g1_weight = _smallest_size_iteration(augmented_g2_sig_nf, g1_sig_nf, g2_num_sinks, g1_num_boundaries, g1_num_sinks, quiet=quiet)
    return g2_g1_weight is None
