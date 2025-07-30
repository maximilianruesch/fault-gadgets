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
from collections import defaultdict
from typing import List, Mapping, Tuple, Dict, Iterable, Optional

from pyzx.graph.base import upair
from ... import GadgetGraph, compute_signatures_for_gadgets, add_sinks_for_all_detecting_regions, \
    wrap_adversarial_edge_flip_noise
from ...pauli import Pauli

ET = Tuple[int, int]

class TannerGraph:
    """
    A tanner graph specialised to an adversarial edge flip noise model for ZX diagrams.
    All "faults" are the atomic faults from the noise model.
    Composite faults must be constructed by the consumer of this data structure.

    Note that edge flips on boundary edges ARE considered if present in the noise model.
    """
    def __init__(self, detectors: List[int], edge_pauli_to_signature: Dict[Tuple[ET, Pauli], Tuple[Dict[int, Pauli], List[int]]]):
        self.detectors = detectors
        self.edge_pauli_to_signature = edge_pauli_to_signature

    def get_violated_detectors(self, edge: ET, flip_type: Pauli) -> Iterable[int]:
        key = (upair(*edge), flip_type)
        if key not in self.edge_pauli_to_signature:
            return []

        return self.edge_pauli_to_signature[key][1]

    def get_boundary_effect(self, edge: ET, flip_type: Pauli) -> Mapping[int, Pauli]:
        key = (upair(*edge), flip_type)
        if key not in self.edge_pauli_to_signature:
            return defaultdict(lambda: Pauli.I)

        return defaultdict(lambda: Pauli.I, [(b, p) for b, p in self.edge_pauli_to_signature[key][0].items()])

    def get_detectors(self) -> Iterable[int]:
        return self.detectors

    def get_faults(self) -> Iterable[Tuple[ET, Pauli]]:
        return self.edge_pauli_to_signature.keys()

    def get_undetected_faults(self) -> Iterable[Tuple[ET, Pauli]]:
        return [k for k, b_ds in self.edge_pauli_to_signature.items() if len(b_ds[1]) == 0]

def extended_tanner_graph_adv_edge_flip_noise(g: GadgetGraph, ideal_edges: Optional[List[Tuple[int, int]]] = None) -> TannerGraph:
    """
    Given a ZX diagram as a graph, computes the tanner graph under the adversarial edge flip noise model, minus the
    provided ideal edges.
    """
    gadget_g, edge_to_gadget_id = wrap_adversarial_edge_flip_noise(g, ideal_edges)
    add_sinks_for_all_detecting_regions(gadget_g)

    return extended_tanner_graph(gadget_g, edge_to_gadget_id)

def extended_tanner_graph(g: GadgetGraph, edge_to_gadget_ids: Mapping[Tuple[int, int], Tuple[int, int, int]]) -> TannerGraph:
    """
    Given a ZX diagram with an edge flip noise model provided via gadgets, computes the tanner graph.
    Requires identification of all gadgets via the edge they were instantiated on.

    The graph must have sufficient sinks in place to open every detecting region that captures at least one gadget.
    """
    id_to_signature = compute_signatures_for_gadgets(g)
    id_to_boundary_flips: Mapping[int, Dict[int, Pauli]] = {
        gadget_id: { b: p for b, p in signature.boundaries.items() }
        for gadget_id, signature in id_to_signature.items()
    }
    id_to_active_sinks: Mapping[int, List[int]] = {
        gadget_id: [sink_id for sink_id, active in signature.sinks.items() if active]
        for gadget_id, signature in id_to_signature.items()
    }
    edge_pauli_to_signature: Dict[Tuple[ET, Pauli], Tuple[Dict[int, Pauli], List[int]]] = dict()
    for edge, gadget_ids in edge_to_gadget_ids.items():
        x_gadget_id, z_gadget_id, y_gadget_id = gadget_ids
        edge_pauli_to_signature[upair(*edge), Pauli.Z] = id_to_boundary_flips[z_gadget_id], id_to_active_sinks[z_gadget_id]
        edge_pauli_to_signature[upair(*edge), Pauli.X] = id_to_boundary_flips[x_gadget_id], id_to_active_sinks[x_gadget_id]
        edge_pauli_to_signature[upair(*edge), Pauli.Y] = id_to_boundary_flips[y_gadget_id], id_to_active_sinks[y_gadget_id]

    return TannerGraph(list(g.sinks().keys()), edge_pauli_to_signature)
