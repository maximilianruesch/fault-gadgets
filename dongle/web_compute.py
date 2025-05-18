from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Optional, Any, List, Tuple, ClassVar

import numpy as np

from pyzx import Mat2, VertexType, is_graph_like, to_gh, EdgeType
from pyzx.editor_actions import match_hadamard_edge
from pyzx.graph.graph_s import GraphS
from pyzx.hsimplify import hadamard_simp
from pyzx.linalg import Z2
from pyzx.pauliweb import PauliWeb
from . import DongleGraph, AdjPauliWeb, Pauli

@dataclass(init=True, repr=False, eq=False, frozen=True)
class GraphOrdering:
    graph_to_ordering: Dict[int, int]
    ordering_to_graph: Dict[int, int]

    z_boundaries: Dict[int, int]
    internal_spiders: List[int]
    pi_2_spiders: List[int]

    def ord(self, s: int) -> int:
        return self.graph_to_ordering[s]

    def graph(self, o: int) -> int:
        return self.ordering_to_graph[o]

class WebAwareTransformation:
    def remove_from(self, web: AdjPauliWeb) -> None:
        raise NotImplementedError()

@dataclass(init=True, repr=False, eq=False, frozen=True)
class ExtraIdNode(WebAwareTransformation):
    node: int

    def remove_from(self, web: AdjPauliWeb) -> None:
        n1, n2 = web.neighbors(self.node)
        sequence = [web[n1, self.node], web[self.node, n1],web[self.node, n2], web[n2, self.node]]
        if len(set(sequence)) != 1:
            raise AssertionError(f"Invalid configuration of id-node {self.node} half edges: {sequence}!")
        web.remove_edges([(n1, self.node), (self.node, n2)])
        web.add_edge((n1, n2), sequence[0])

@dataclass(init=True, repr=False, eq=False, frozen=True)
class ExpandedHadamard(WebAwareTransformation):
    r1_node: int
    r2_node: int
    r3_node: int
    flipped_decomposition: bool

    id_sequence: ClassVar[List[Pauli]] = ['I', 'I', 'I', 'I', 'I', 'I', 'I', 'I']
    y_sequence: ClassVar[List[Pauli]] = ['Y', 'Y', 'X', 'X', 'X', 'X', 'Y', 'Y']
    zx_sequence: ClassVar[List[Pauli]] = ['Z', 'Z', 'Z', 'Z', 'Y', 'Y', 'X', 'X']
    xz_sequence: ClassVar[List[Pauli]] = ['X', 'X', 'Y', 'Y', 'Z', 'Z', 'Z', 'Z']

    def _sequence_valid(self, sequence: List[Pauli]) -> bool:
        if sequence == ExpandedHadamard.id_sequence:
            return True

        if self.flipped_decomposition and (
            sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.zx_sequence))
                or sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.xz_sequence))
                or sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.y_sequence))
        ):
            return True
        elif sequence == ExpandedHadamard.zx_sequence\
                or sequence == ExpandedHadamard.xz_sequence\
                or sequence == ExpandedHadamard.y_sequence:
            return True

        return False


    def remove_from(self, web: AdjPauliWeb) -> None:
        w1, w2, w3 = self.r1_node, self.r2_node, self.r3_node
        w1_left, w1_right = web.neighbors(w1)
        w1_ext = w1_left if w1_right == w2 else w1_right
        w3_left, w3_right = web.neighbors(w3)
        w3_ext = w3_right if w3_left == w2 else w3_left

        sequence = [
            web[w1_ext, w1], web[w1, w1_ext],
            web[w1, w2], web[w2, w1],
            web[w2, w3], web[w3, w2],
            web[w3, w3_ext], web[w3_ext, w3]
        ]
        if not self._sequence_valid(sequence):
            raise AssertionError(f"Invalid configuration of H-nodes {str((w1, w2, w3))} half edges: {sequence}!")

        web.remove_edges([(w1_ext, w1), (w1, w2), (w2, w3), (w3, w3_ext)])
        web.add_half_edge((w1_ext, w3_ext), sequence[0])
        web.add_half_edge((w3_ext, w1_ext), sequence[-1])

def _place_node_between(g: GraphS, _type: VertexType, n1: int, n2: int) -> int:
    node = g.add_vertex(_type)
    n1_qubit, n1_row = g.qubit(n1), g.row(n1)
    n2_qubit, n2_row = g.qubit(n2), g.row(n2)
    if n1_qubit == n2_qubit:  # Horizontal
        g.set_qubit(node, n1_qubit)
        g.set_row(node, n1_row + (n2_row - n1_row) * (float(1) / 2))
    elif n1_row == n2_row:  # Vertical
        g.set_qubit(node, n1_qubit + (n2_qubit - n1_qubit) * (float(1) / 2))
        g.set_row(node, n1_row)

    g.remove_edge((n1, n2))
    g.add_edges([(n1, node), (node, n2)])

    return node

def _euler_expand_edges(g: GraphS) -> List[ExpandedHadamard]:
    """
    A cut down version of pyzx.euler_expansion which does not add global scalars and does not prematurely 'merge' spiders
    """
    decomposition_xzx = [VertexType.X, VertexType.Z, VertexType.X]
    decomposition_zxz = [VertexType.Z, VertexType.X, VertexType.Z]

    expanded_edges = []
    for v1, v2 in match_hadamard_edge(g):
        flip = g.type(v1) == g.type(v2) and g.type(v1) == VertexType.Z
            # Change decomposition to avoid introducing more X-spiders due to adjacent Z-spider
        pattern = decomposition_xzx if flip else decomposition_zxz

        w2 = _place_node_between(g, pattern[1], v1, v2)
        g.add_to_phase(w2, Fraction(1, 2))
        w1 = _place_node_between(g, pattern[0], v1, w2)
        g.add_to_phase(w1, Fraction(1, 2))
        w3 = _place_node_between(g, pattern[2], w2, v2)
        g.add_to_phase(w3, Fraction(1, 2))

        expanded_edges.append(ExpandedHadamard(w1, w2, w3, flipped_decomposition=flip))

    return expanded_edges

def _to_red_green_graphlike(g: GraphS, debug: Optional[Dict[str, Any]] = None) -> Tuple[List[ExtraIdNode], List[ExpandedHadamard]]:
    # Convert all H-edges and Hadamards to red and green spiders
    hadamard_simp(g, quiet=True)
    expanded_hadamards = _euler_expand_edges(g)

    # Verify that diagram is clifford
    offending_vertices = []
    for v in g.vertices():
        v_type = g.type(v)
        if g.phase(v).denominator > 2 or\
            (v_type != VertexType.Z and v_type != VertexType.X and v_type != VertexType.BOUNDARY):
            offending_vertices.append(v)
    if len(offending_vertices) > 0:
        if debug is not None:
            debug['offending_vertices'] = offending_vertices

        raise AssertionError(f"Given diagram is not a clifford diagram up to hadamard expansion. The following "
                             f"vertices are either not of type X,Z,BOUNDARY or have a non-clifford "
                             f"phase: {', '.join(map(str, offending_vertices))}")
    offending_edges = [e for e in g.edges() if g.edge_type(e) != EdgeType.SIMPLE]
    if len(offending_edges) > 0:
        if debug is not None:
            debug['offending_edges'] = offending_edges

        raise AssertionError(f"Given diagram is not a clifford diagram up to hadamard expansion. The following "
                             f"edges are not simple edges: {', '.join(map(str, offending_edges))}")

    # Introduce intermediate nodes
    new_nodes = []
    for s, t in list(g.edges()):
        if g.type(s) == g.type(t):
            if g.type(s) == VertexType.BOUNDARY or g.type(s) == VertexType.Z:
                new_type = VertexType.X
            else:
                new_type = VertexType.Z
            new_nodes.append(ExtraIdNode(_place_node_between(g, new_type, s, t)))

    # Ensure boundaries are not connected to a red spider
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        if g.type(neighbour) == VertexType.X:
            new_nodes.append(ExtraIdNode(_place_node_between(g, VertexType.Z, boundary, neighbour)))

    # Ensure boundaries are not connected to green spiders with nonzero phase or more than one boundary connection
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        neighbour_boundaries = [v for v in g.neighbors(neighbour) if g.type(v) == VertexType.BOUNDARY]
        if g.phase(neighbour) != 0 or len(neighbour_boundaries) > 1:
            new_x = ExtraIdNode(_place_node_between(g, VertexType.X, boundary, neighbour))
            new_nodes.append(new_x)
            new_nodes.append(ExtraIdNode(_place_node_between(g, VertexType.Z, boundary, new_x.node)))

    if debug is not None:
        debug['g'] = g
        debug['new_nodes'] = new_nodes
        debug['boundaries'] = boundaries
        gc = g.clone(DongleGraph())
        to_gh(gc)
        debug['gh'] = gc
        debug['graphlike'] = is_graph_like(gc, strict=True)

    return new_nodes, expanded_hadamards

def _determine_ordering(g: GraphS, debug: Optional[Dict[str, Any]] = None) -> GraphOrdering:
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    z_boundaries = {list(g.neighbors(b))[0]: b for b in boundaries}
    internal_spiders = list(g.vertex_set().difference(boundaries).difference(z_boundaries.keys()))
    pi_2_spiders = list(filter(lambda _v: g.phase(_v).denominator == 2, internal_spiders))

    if debug is not None:
        debug['z_boundaries'] = z_boundaries
        debug['z_boundaries_types'] = list(map(lambda _v: g.type(_v), z_boundaries.keys()))

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

def _create_firing_verification(g: GraphS, ordering: GraphOrdering, debug: Optional[Dict[str, Any]] = None) -> Mat2:
    num_z_boundaries = len(ordering.z_boundaries)
    num_non_boundary_spiders = num_z_boundaries + len(ordering.internal_spiders)
    adj_matrix = Mat2.zeros(num_non_boundary_spiders, num_non_boundary_spiders)
    for s in g.graph:
        for t in g.graph[s]:
            if g.type(s) != VertexType.BOUNDARY and g.type(t) != VertexType.BOUNDARY:
                adj_matrix[ordering.ord(s), ordering.ord(t)] += 1

    if debug is not None:
        debug['adj_matrix'] = adj_matrix

    m_d = Mat2.zeros(adj_matrix.rows(), adj_matrix.cols() + num_z_boundaries)
    m_d[0:num_z_boundaries, 0:num_z_boundaries] = Mat2.id(num_z_boundaries)
    m_d[:, num_z_boundaries:] = adj_matrix
    num_pi_2 = len(ordering.pi_2_spiders)
    slice_key = (slice(m_d.rows() - num_pi_2, m_d.rows()), slice(m_d.cols() - num_pi_2, m_d.cols()))
    m_d[slice_key] = Mat2((np.array(m_d[slice_key].data, dtype=bool) ^ np.array(Mat2.id(num_pi_2).data, dtype=bool)).tolist())

    if debug is not None:
        debug['M_D'] = m_d

    return m_d

def _convert_firing_assignment_to_g_web(g: GraphS, ordering: GraphOrdering, v: List[Z2]) -> PauliWeb:
    g_web = PauliWeb(g)

    # Fire all green spiders with full red edges and thus their red neighbours
    for adj_vertex, g_vertex in ordering.ordering_to_graph.items():
        g_type = g.type(g_vertex)
        if g_type == VertexType.Z and v[adj_vertex + len(ordering.z_boundaries)] == 1:
            for _n in g.neighbors(g_vertex):
                g_web.add_edge((g_vertex, _n), 'X')

    # Fire all red spiders with full green edges and thus their green neighbours
    for adj_vertex, g_vertex in ordering.ordering_to_graph.items():
        g_type = g.type(g_vertex)
        if g_type == VertexType.X and v[adj_vertex + len(ordering.z_boundaries)] == 1:
            for _n in g.neighbors(g_vertex):
                g_web.add_edge((g_vertex, _n), 'Z')

    # Fire all green output edges
    for g_z_boundary, g_boundary in ordering.z_boundaries.items():
        adj_z_boundary = ordering.ord(g_z_boundary)
        if v[adj_z_boundary] == 1:
            g_web.add_edge((g_z_boundary, g_boundary), 'Z')

    return g_web

def _reduce_g_web_to_original_web(
        new_nodes: List[ExtraIdNode],
        expanded_hadamards: List[ExpandedHadamard],
        g_web: PauliWeb
) -> AdjPauliWeb:
    adj_web = AdjPauliWeb.from_regular_web(g_web)
    for n in new_nodes:
        n.remove_from(adj_web)
    for h in expanded_hadamards:
        h.remove_from(adj_web)
    return adj_web

def compute_webs(graph: GraphS, debug: Optional[Dict[str, Any]] = None) -> List[AdjPauliWeb]:
    g = graph.clone(GraphS())
    if debug is not None:
        debug['g'] = g

    new_nodes, expanded_hadamards = _to_red_green_graphlike(g, debug)
    ordering = _determine_ordering(g, debug)
    m_d = _create_firing_verification(g, ordering, debug)

    # Compute span of space of valid firing assignments
    sols = m_d.nullspace()
    if debug is not None:
        debug['sols'] = sols

    g_webs = list(map(lambda v: _convert_firing_assignment_to_g_web(g, ordering, v), sols))
    if debug is not None:
        debug['g_webs'] = g_webs

    return list(map(lambda web: _reduce_g_web_to_original_web(new_nodes, expanded_hadamards, web), g_webs))

def compute_web_for_dongle(graph: DongleGraph, dongle_id: int, debug: Optional[Dict[str, Any]] = None) -> AdjPauliWeb:
    """
    Computes a Pauli web for the given dongle in the graph context.
    A valid web for the dongle is one that features a Z-type edge between the dongles spawn and distributor.
    """

    g = graph.clone(DongleGraph())
    g.full_instance()

    dongle = g.dongles()[dongle_id]
    g.set_type(dongle.spawn, VertexType.BOUNDARY)

    # Computing webs
    new_nodes, expanded_hadamards = _to_red_green_graphlike(g, debug)
    ordering = _determine_ordering(g, debug)
    m_d = _create_firing_verification(g, ordering, debug)
    sols = m_d.nullspace()

    spawn_z_boundary_index = ordering.ord(list(g.neighbors(dongle.spawn))[0])
    sol_types = [
        Pauli.from_binary(
            z_flip=sol[spawn_z_boundary_index],
            x_flip=sol[spawn_z_boundary_index + len(ordering.z_boundaries)]
        ) for sol in sols
    ]

    # Fitting web is given directly, note that it might not be minimal in weight overall
    if Pauli.Z in sol_types:
        z_sols = [web for i, web in enumerate(sols) if sol_types[i] == Pauli.Z]
        z_g_webs = map(lambda v: _convert_firing_assignment_to_g_web(g, ordering, v), z_sols)
        z_webs = map(lambda web: _reduce_g_web_to_original_web(new_nodes, expanded_hadamards, web), z_g_webs)
        min_web = min(z_webs, key=lambda web: sum([1 if pauli != 'I' else 0 for pauli in web.half_edges().values()]))

        return min_web

    # Compute fitting web by complementing a Y web with an X web to yield a Z web
    if Pauli.X in sol_types and Pauli.Y in sol_types:
        x_sol = sols[sol_types.index(Pauli.X)]
        y_sol = sols[sol_types.index(Pauli.Y)]

        x_web = _reduce_g_web_to_original_web(
            new_nodes,
            expanded_hadamards,
            _convert_firing_assignment_to_g_web(g, ordering, x_sol)
        )
        y_web = _reduce_g_web_to_original_web(
            new_nodes,
            expanded_hadamards,
            _convert_firing_assignment_to_g_web(g, ordering, y_sol)
        )

        return x_web * y_web

    raise AssertionError(f"No fitting webs found for dongle {dongle}!")
