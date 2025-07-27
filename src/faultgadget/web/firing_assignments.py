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
from typing import Dict, List, NamedTuple, Mapping

import numpy as np

from pyzx import Mat2, VertexType
from pyzx.graph.graph_s import GraphS
from pyzx.linalg import Z2

from ..pauli import Pauli, PauliWeb
from ..signature import Signature

class GraphOrdering(NamedTuple):
    graph_to_ordering: Dict[int, int]
    ordering_to_graph: Dict[int, int]

    z_boundaries: Dict[int, int]
    internal_spiders: List[int]
    pi_2_spiders: List[int]

    def ord(self, s: int) -> int:
        return self.graph_to_ordering[s]

    def graph(self, o: int) -> int:
        return self.ordering_to_graph[o]

def determine_ordering(g: GraphS) -> GraphOrdering:
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    z_boundaries = {list(g.neighbors(b))[0]: b for b in boundaries}
    internal_spiders = list(g.vertex_set().difference(boundaries).difference(z_boundaries.keys()))
    pi_2_spiders = list(filter(lambda _v: g.phase(_v).denominator == 2, internal_spiders))

    graph_to_ordering: Dict[int, int] = dict()
    ordering_to_graph: Dict[int, int] = dict()
    idx = 0
    for boundary in z_boundaries.keys():
        graph_to_ordering[boundary] = idx
        ordering_to_graph[idx] = boundary
        idx += 1
    for internal in set(internal_spiders).difference(pi_2_spiders):
        graph_to_ordering[internal] = idx
        ordering_to_graph[idx] = internal
        idx += 1
    for pi_2_spider in pi_2_spiders:
        graph_to_ordering[pi_2_spider] = idx
        ordering_to_graph[idx] = pi_2_spider
        idx += 1
        
    return GraphOrdering(graph_to_ordering, ordering_to_graph, z_boundaries, internal_spiders, pi_2_spiders)

def create_firing_verification(g: GraphS, ordering: GraphOrdering) -> Mat2:
    num_z_boundaries = len(ordering.z_boundaries)
    num_non_boundary_spiders = num_z_boundaries + len(ordering.internal_spiders)
    adj_matrix = Mat2.zeros(num_non_boundary_spiders, num_non_boundary_spiders)
    for s in g.graph:
        for t in g.graph[s]:
            if g.type(s) != VertexType.BOUNDARY and g.type(t) != VertexType.BOUNDARY:
                adj_matrix[ordering.ord(s), ordering.ord(t)] += 1

    m_d = Mat2.zeros(adj_matrix.rows(), adj_matrix.cols() + num_z_boundaries)
    m_d[0:num_z_boundaries, 0:num_z_boundaries] = Mat2.id(num_z_boundaries)
    m_d[:, num_z_boundaries:] = adj_matrix
    num_pi_2 = len(ordering.pi_2_spiders)
    slice_key = (slice(m_d.rows() - num_pi_2, m_d.rows()), slice(m_d.cols() - num_pi_2, m_d.cols()))
    m_d[slice_key] = Mat2((np.array(m_d[slice_key].data, dtype=bool) ^ np.array(Mat2.id(num_pi_2).data, dtype=bool)).tolist())

    return m_d

def convert_firing_assignment_to_web(g: GraphS, ordering: GraphOrdering, v: List[Z2]) -> PauliWeb:
    g_web = PauliWeb()

    for adj_vertex, g_vertex in ordering.ordering_to_graph.items():
        g_type = g.type(g_vertex)
        # Fire all green spiders with full red edges and thus their red neighbours
        if g_type == VertexType.Z and v[adj_vertex + len(ordering.z_boundaries)] == 1:
            for _n in g.neighbors(g_vertex):
                g_web.add_edge((g_vertex, _n), Pauli.X)
        # Fire all red spiders with full green edges and thus their green neighbours
        if g_type == VertexType.X and v[adj_vertex + len(ordering.z_boundaries)] == 1:
            for _n in g.neighbors(g_vertex):
                g_web.add_edge((g_vertex, _n), Pauli.Z)

    # Fire all green output edges
    for g_z_boundary, g_boundary in ordering.z_boundaries.items():
        adj_z_boundary = ordering.ord(g_z_boundary)
        if v[adj_z_boundary] == 1:
            g_web.add_edge((g_z_boundary, g_boundary), Pauli.Z)

    return g_web

def convert_firing_assignment_to_signature(ordering: GraphOrdering, v: List[Z2]) -> Signature:
    boundaries: Mapping[int, Pauli] = defaultdict(lambda: Pauli.I)

    # Read signature directly from output edges
    for g_z_boundary, g_boundary in ordering.z_boundaries.items():
        adj_z_boundary = ordering.ord(g_z_boundary)
        if v[adj_z_boundary] == 1:
            boundaries[g_boundary] *= Pauli.Z
        if v[adj_z_boundary + len(ordering.z_boundaries)] == 1:
            boundaries[g_boundary] *= Pauli.X

    return Signature(boundaries, dict())
