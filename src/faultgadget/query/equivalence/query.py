# Copyright 2025 Maximilian Rüsch
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List, Mapping, Tuple

import numpy as np
from galois import GF2

from pyzx import VertexType
from pyzx.graph.graph_s import GraphS
from ...gadget_web_compute import compute_signatures_for_gadgets
from ...graph_helpers import add_sinks_for_all_detecting_regions
from ...graph import GadgetGraph
from ...web import compute_stabiliser_signatures
from .enumeration import _smallest_size_iteration
from ...signature import Signature
from ...pauli import Pauli

ET = Tuple[int, int]

def _index_graph_boundaries(g: GraphS) -> Tuple[Mapping[int, int], int]:
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    return { b: i for i, b in enumerate(boundaries)}, len(boundaries)

def _index_graph_sinks(g: GadgetGraph) -> Tuple[Mapping[int, int], int]:
    sink_id_to_idx = { s: i for i, s in enumerate(g.sinks().keys()) }
    num_sinks = len(sink_id_to_idx)

    return sink_id_to_idx, num_sinks

class Stabilisers:
    def __init__(self, stabiliser_rref: GF2):
        self._rref = stabiliser_rref
        self._indices = self._rref.argmax(axis=1).view(np.ndarray)

    def normalise_signatures(self, sigs: GF2) -> GF2:
        return sigs + sigs[:, self._indices] @ self._rref

class AugmentedStabilisers:
    _rref: GF2
    _indices: np.ndarray

    @staticmethod
    def from_stabilisers(stabilisers: Stabilisers, num_sinks: int) -> 'AugmentedStabilisers':
        self = AugmentedStabilisers()
        self._rref = GF2(np.hstack([stabilisers._rref, GF2.Zeros((len(stabilisers._rref), num_sinks))]))
        self._indices = stabilisers._indices

        return self

    def normalise_signature(self, sig: GF2) -> GF2: # TODO remove
        return self.normalise_signatures(GF2([sig]))[0]

    def normalise_signatures(self, sigs: GF2) -> GF2:
        return sigs + sigs[:, self._indices] @ self._rref

def _stabilisers(g: GraphS, boundaries_to_idx: Mapping[int, int]) -> Stabilisers:
    stabilisers = compute_stabiliser_signatures(g)  # TODO if strict, compute stabilisers of g2 and assert space equality
    num_boundaries = len(boundaries_to_idx)
    np_stabilisers = np.zeros((len(stabilisers), num_boundaries * 2), dtype=int)
    for i, stab in enumerate(stabilisers):
        for boundary, pauli in stab.boundaries.items():
            idx = boundaries_to_idx[boundary]
            if pauli == Pauli.Z or pauli == Pauli.Y: np_stabilisers[i, idx] = 1
            if pauli == Pauli.X or pauli == Pauli.Y: np_stabilisers[i, idx + num_boundaries] = 1

    return Stabilisers(GF2(np_stabilisers).row_reduce(eye='left'))

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

def _construct_signatures(g: GraphS, stabilisers: Stabilisers, boundaries_to_idx: Mapping[int, int],
                          num_boundaries: int) -> Tuple[AugmentedStabilisers, List[GF2], int]:
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    sink_id_to_idx, num_sinks = _index_graph_sinks(gadget_graph)

    _add_gadgets(gadget_graph)
    signatures = compute_signatures_for_gadgets(gadget_graph, gadget_graph.gadgets().keys())
    # Remove trivial signatures # TODO remove once somewhere...
    signatures = { _id: signature for _id, signature in signatures.items() if not signature.is_trivial() }

    stabs = AugmentedStabilisers.from_stabilisers(stabilisers, num_sinks)
    sig_nf = _calculate_signature_normal_forms(signatures, stabs, boundaries_to_idx, num_boundaries, sink_id_to_idx, num_sinks)

    return stabs, sig_nf, num_sinks

def _boundary_signatures(stabs: Stabilisers, num_boundaries: int) -> GF2:
    sigs = []
    for i in range(num_boundaries):
        # Z Signature
        x_atomic_sig = GF2.Zeros(num_boundaries * 2)
        x_atomic_sig[i] = 1
        sigs.append(x_atomic_sig)
        # X Signature
        z_atomic_sig = GF2.Zeros(num_boundaries * 2)
        z_atomic_sig[i + num_boundaries] = 1
        sigs.append(z_atomic_sig)
        # Y Signature
        sigs.append(x_atomic_sig + z_atomic_sig)

    return stabs.normalise_signatures(GF2(sigs))

def _add_boundary_signatures(sig_nf: List[GF2], boundary_signatures: GF2,  num_sinks: int) -> List[GF2]:
    augmented_sig_nf = sig_nf.copy()
    augmented_sig_nf.extend(np.hstack([boundary_signatures, GF2.Zeros((len(boundary_signatures), num_sinks))]))

    return [GF2(l) for l in np.unique(augmented_sig_nf, axis=0)]

def is_fault_equivalent(g1: GraphS, g2: GraphS, quiet: bool = True) -> bool:
    """
    Given two diagrams g1 and g2, determine if they are fault equivalent under the edge flip noise model.
    """
    g1_boundaries_to_idx, g1_num_boundaries = _index_graph_boundaries(g1) # TODO index boundaries the same way / force the same inputs / outputs
    g2_boundaries_to_idx, g2_num_boundaries = _index_graph_boundaries(g2)
    if g1_num_boundaries != g2_num_boundaries:
        raise RuntimeError("Number of boundaries in graphs must be the same!")

    if not quiet: print("Computing stabilisers...")
    stabilisers = _stabilisers(g1, g1_boundaries_to_idx)

    if not quiet: print("Computing boundary signatures...")
    boundary_signatures = _boundary_signatures(stabilisers, g1_num_boundaries)

    if not quiet: print("Constructing signatures of g1...")
    g1_stabs, g1_sig_nf, g1_num_sinks = _construct_signatures(g1, stabilisers, g1_boundaries_to_idx, g1_num_boundaries)
    if not quiet: print(f"Retrieved {len(g1_sig_nf)} signatures for g1!")

    if not quiet: print("Constructing signatures of g2...")
    g2_stabs, g2_sig_nf, g2_num_sinks = _construct_signatures(g2, stabilisers, g2_boundaries_to_idx, g2_num_boundaries)
    if not quiet: print(f"Retrieved {len(g2_sig_nf)} signatures for g2!")

    if not quiet: print("Checking if g1 -> g2 is fault bounded...")
    augmented_g1_sig_nf = _add_boundary_signatures(g1_sig_nf, boundary_signatures, g1_num_sinks)
    g1_g2_weight = _smallest_size_iteration(augmented_g1_sig_nf, g2_sig_nf, g1_num_sinks, g2_num_boundaries, g2_num_sinks, quiet=quiet)
    if g1_g2_weight is not None:
        return False

    if not quiet: print("Checking if g2 -> g1 is fault bounded...")
    augmented_g2_sig_nf = _add_boundary_signatures(g2_sig_nf, boundary_signatures, g2_num_sinks)
    g2_g1_weight = _smallest_size_iteration(augmented_g2_sig_nf, g1_sig_nf, g2_num_sinks, g1_num_boundaries, g1_num_sinks, quiet=quiet)
    return g2_g1_weight is None
