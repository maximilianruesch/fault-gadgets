from fractions import Fraction
from typing import Dict, Optional, Any, List, Tuple

import numpy as np

from pyzx import Mat2, VertexType, is_graph_like, to_gh, EdgeType
from pyzx.editor_actions import match_hadamard_edge
from pyzx.hsimplify import hadamard_simp
from pyzx.linalg import Z2
from pyzx.pauliweb import PauliWeb
from pyzx.utils import toggle_vertex
from . import ShieldedGraph, AdjPauliWeb


def _place_node_between(g: ShieldedGraph, _type: VertexType, n1: int, n2: int) -> int:
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

def _euler_expand_edges(g: ShieldedGraph) -> List[Tuple[int, int, int]]:
    """
    A cut down version of pyzx.euler_expansion which does not add global scalars and does not prematurely 'merge' spiders
    """
    expanded_edges = []
    for v1, v2 in match_hadamard_edge(g):
        w2 = _place_node_between(g, VertexType.X, v1, v2)
        g.add_to_phase(w2, Fraction(1, 2))
        w1 = _place_node_between(g, VertexType.Z, v1, w2)
        g.add_to_phase(w1, Fraction(1, 2))
        w3 = _place_node_between(g, VertexType.Z, w2, v2)
        g.add_to_phase(w3, Fraction(1, 2))

        expanded_edges.append((w1, w2, w3))

    return expanded_edges

def _to_red_green_graphlike(graph: ShieldedGraph, debug: Optional[Dict[str, Any]] = None) -> Tuple[ShieldedGraph, List[int], List[Tuple[int, int, int]]]:
    g = graph.clone(ShieldedGraph())
    g.full_instance(h_edges=True)

    # Convert all H-edges and H-boxes to red and green spiders
    hadamard_simp(g, quiet=True)
    if debug is not None:
        debug['g'] = g
    expanded_hadamards = _euler_expand_edges(g)

    if debug is not None:
        debug['g'] = g

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
            new_nodes.append(_place_node_between(g, toggle_vertex(g.type(s)), s, t))

    for dongle in graph.dongles():
        g.set_type(dongle.spawn, VertexType.BOUNDARY)

    # Ensure boundaries are not connected to a red spider
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        if g.type(neighbour) == VertexType.X:
            new_nodes.append(_place_node_between(g, VertexType.Z, boundary, neighbour))

    # Ensure boundaries are not connected to green spiders with nonzero phase or more than one boundary connection
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        neighbour_boundaries = [v for v in g.neighbors(neighbour) if g.type(v) == VertexType.BOUNDARY]
        if g.phase(neighbour) != 0 or len(neighbour_boundaries) > 1:
            new_x = _place_node_between(g, VertexType.X, boundary, neighbour)
            new_nodes.append(new_x)
            new_nodes.append(_place_node_between(g, VertexType.Z, boundary, new_x))

    if debug is not None:
        debug['g'] = g
        debug['new_nodes'] = new_nodes
        debug['boundaries'] = boundaries
        gc = g.clone(ShieldedGraph())
        to_gh(gc)
        debug['gh'] = gc
        debug['graphlike'] = is_graph_like(gc, strict=True)

    return g, new_nodes, expanded_hadamards

def _determine_ordering(g: ShieldedGraph, debug: Optional[Dict[str, Any]] = None) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int], List[int], List[int]]:
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
        
    return graph_to_ordering, ordering_to_graph, z_boundaries, internal_spiders, pi_2_spiders

def _solve_firing_verification(
        g: ShieldedGraph,
        graph_to_ordering: Dict[int, int],
        z_boundaries: Dict[int, int],
        internal_spiders: List[int],
        pi_2_spiders: List[int],
        debug: Optional[Dict[str, Any]] = None
) -> List[List[int]]:
    num_z_boundaries = len(z_boundaries)
    num_non_boundary_spiders = num_z_boundaries + len(internal_spiders)
    adj_matrix = Mat2.zeros(num_non_boundary_spiders, num_non_boundary_spiders)
    for s in g.graph:
        for t in g.graph[s]:
            if g.type(s) != VertexType.BOUNDARY and g.type(t) != VertexType.BOUNDARY:
                adj_matrix[graph_to_ordering[s], graph_to_ordering[t]] += 1

    if debug is not None:
        debug['adj_matrix'] = adj_matrix

    # TODO add requirement that dongle must be fired? Or just search in solution space?
    m_d = Mat2.zeros(adj_matrix.rows(), adj_matrix.cols() + num_z_boundaries)
    m_d[0:num_z_boundaries, 0:num_z_boundaries] = Mat2.id(num_z_boundaries)
    m_d[:, num_z_boundaries:] = adj_matrix
    num_pi_2 = len(pi_2_spiders)
    slice_key = (slice(m_d.rows() - num_pi_2, m_d.rows()), slice(m_d.cols() - num_pi_2, m_d.cols()))
    m_d[slice_key] = Mat2((np.array(m_d[slice_key].data) - np.array(Mat2.id(num_pi_2).data)).tolist())

    if debug is not None:
        debug['M_D'] = m_d

    # Compute span of space of valid firing assignments
    sols = m_d.nullspace()
    non_trivial_sols = list(filter(lambda _sol: sum(_sol[:2 * num_z_boundaries]) != 0, sols))
    if debug is not None:
        debug['sols'] = sols
        debug['non_trivial_sols'] = non_trivial_sols

    return non_trivial_sols

def web_compute(graph: ShieldedGraph, debug: Optional[Dict[str, Any]] = None) -> List[PauliWeb]:
    g, new_nodes, expanded_hadamards = _to_red_green_graphlike(graph, debug)

    graph_to_ordering, ordering_to_graph, z_boundaries, internal_spiders, pi_2_spiders = _determine_ordering(g, debug)

    non_trivial_sols = _solve_firing_verification(g, graph_to_ordering, z_boundaries, internal_spiders, pi_2_spiders, debug)

    def _convert_to_g_web(v: List[Z2]) -> PauliWeb:
        g_web = PauliWeb(g)

        # Fire all green spiders with full red edges and thus their red neighbours
        for adj_vertex, g_vertex in ordering_to_graph.items():
            g_type = g.type(g_vertex)
            if g_type == VertexType.Z and v[adj_vertex + len(z_boundaries)] == 1:
                for _n in g.neighbors(g_vertex):
                    g_web.add_edge((g_vertex, _n), 'X')

        # Fire all red spiders with full green edges and thus their green neighbours
        for adj_vertex, g_vertex in ordering_to_graph.items():
            g_type = g.type(g_vertex)
            if g_type == VertexType.X and v[adj_vertex + len(z_boundaries)] == 1:
                for _n in g.neighbors(g_vertex):
                    g_web.add_edge((g_vertex, _n), 'Z')

        # Fire all green output edges
        for g_z_boundary, g_boundary in z_boundaries.items():
            adj_z_boundary = graph_to_ordering[g_z_boundary]
            if v[adj_z_boundary] == 1:
                g_web.add_edge((g_z_boundary, g_boundary), 'Z')

        return g_web

    g_webs = list(map(_convert_to_g_web, non_trivial_sols))
    if debug is not None:
        debug['g_webs'] = g_webs

    def _reduce(g_web: PauliWeb) -> PauliWeb:
        adj_web = AdjPauliWeb.from_regular_web(g_web)
        for n in new_nodes:
            adj_web.remove_id(n)
        for h in expanded_hadamards:
            adj_web.remove_hadamard(h)
        return adj_web.to_regular_web(graph)

    return list(map(_reduce, g_webs))
