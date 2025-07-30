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

from typing import List, Optional, Union, Tuple, Mapping, Set

from faultgadget import GadgetGraph
from pyzx.graph.base import upair
from pyzx.graph.graph_s import GraphS

def wrap_adversarial_edge_flip_noise(g: Union[GraphS, GadgetGraph], ideal_edges: Optional[List[Tuple[int, int]]] = None)\
        -> Tuple[GadgetGraph, Mapping[Tuple[int, int], Tuple[int, int, int]]]:
    """
    :returns: A copy of the graph that models adversarial edge flip noise on all edges not contained in idealised_edges
        and a mapping of (normalised) edges to (X, Z, Y) gadget ids (only defined for non-idealised edges)
    """
    _ideal_edges: Set[Tuple[int, int]] = { upair(*edge) for edge in (ideal_edges or []) }
    if isinstance(g, GraphS):
        gadget_graph = GadgetGraph.from_graph(g)
    else:
        gadget_graph = g

    edge_to_gadget_ids = {
        upair(*edge): gadget_graph.add_edge_flip_gadgets(edge) for edge in gadget_graph.edges()
        if upair(*edge) not in _ideal_edges
    }

    return gadget_graph, edge_to_gadget_ids
