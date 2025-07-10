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

from typing import List, Mapping, Tuple, Dict, Iterable

from pyzx.graph.base import upair
from pyzx.graph.graph_s import GraphS
from ... import add_all_gadgets, GadgetGraph, add_sinks_for_all_detecting_regions, compute_signatures_for_gadgets
from ...pauli import Pauli

ET = Tuple[int, int]

class TannerGraph:
    """
    A tanner graph specialised to an adversarial edge flip noise model for ZX diagrams.
    All "faults" are the atomic faults from the noise model.
    Composite faults must be constructed by the consumer of this data structure.

    Note that edge flips on boundary edges ARE considered if present in the noise model.
    """
    def __init__(self, detectors: List[int], edge_pauli_to_detectors: Dict[Tuple[ET, Pauli], List[int]]):
        self.detectors = detectors
        self.edge_pauli_to_detectors = edge_pauli_to_detectors

    def get_violated_detectors(self, edge: ET, flip_type: Pauli) -> Iterable[int]:
        return self.edge_pauli_to_detectors[upair(*edge), flip_type]

    def get_detectors(self) -> Iterable[int]:
        return self.detectors

    def get_faults(self) -> Iterable[Tuple[ET, Pauli]]:
        return self.edge_pauli_to_detectors.keys()

    def get_undetected_faults(self) -> Iterable[Tuple[ET, Pauli]]:
        return [k for k, ds in self.edge_pauli_to_detectors.items() if len(ds) == 0]

def tanner_graph(g: GraphS) -> TannerGraph:
    """
    Given a ZX diagram as a graph, computes the tanner graph under the adversarial edge flip noise model.
    """
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    edge_to_gadget_ids = add_all_gadgets(gadget_graph)
    id_to_signature = compute_signatures_for_gadgets(gadget_graph)

    id_to_active_sinks: Mapping[int, List[int]] = {
        gadget_id: [sink_id for sink_id, active in signature.sinks.items() if active]
        for gadget_id, signature in id_to_signature.items()
    }
    edge_pauli_to_active_sinks: Dict[Tuple[ET, Pauli], List[int]] = dict()
    for edge, gadget_ids in edge_to_gadget_ids.items():
        x_gadget_id, z_gadget_id, y_gadget_id = gadget_ids
        edge_pauli_to_active_sinks[upair(*edge), Pauli.Z] = id_to_active_sinks[z_gadget_id]
        edge_pauli_to_active_sinks[upair(*edge), Pauli.X] = id_to_active_sinks[x_gadget_id]
        edge_pauli_to_active_sinks[upair(*edge), Pauli.Y] = id_to_active_sinks[y_gadget_id]

    return TannerGraph(list(gadget_graph.sinks().keys()), edge_pauli_to_active_sinks)
