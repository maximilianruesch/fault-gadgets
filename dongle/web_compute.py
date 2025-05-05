from fractions import Fraction
from typing import Dict, Optional, Any, List

from pyzx import Mat2, VertexType, EdgeType, is_graph_like, to_gh
from pyzx.linalg import Z2
from pyzx.pauliweb import PauliWeb
from pyzx.utils import toggle_vertex
from . import ShieldedGraph

ALLOWED_TYPES = [VertexType.Z, VertexType.X, VertexType.BOUNDARY]

def place_node_between(g: ShieldedGraph, _type: VertexType, n1: int, n2: int) -> int:
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

def web_compute(graph: ShieldedGraph, debug: Optional[Dict[str, Any]] = None) -> List[PauliWeb]:
    g = graph.clone(ShieldedGraph())
    g.full_instance(h_edges=False) # TODO handle already existing h edges? Maybe with had_edge_to_hbox?
    # Put into graph like ZX form by introducing extra nodes
    new_nodes = []
    for edge in list(g.edges()): # TODO Make sure to copy algorithm 1 exactly except introducing new nodes in between same color instead of fusing them
        if g.edge_type(edge) != EdgeType.SIMPLE:
            raise ValueError(f"May only handle simple edges for now, {g.edge_type(edge)} given!")

        s,t = edge
        s_type = g.type(s)
        t_type = g.type(t)
        if not s_type in ALLOWED_TYPES or not t_type in ALLOWED_TYPES:
            raise ValueError(f"May only handle vertex types {','.join(map(lambda _t: _t.name, ALLOWED_TYPES))} for now, {s_type.name} and {t_type.name} given!")

        if s_type == t_type:
            new_nodes.append(place_node_between(g, toggle_vertex(s_type), s, t))
    for dongle in graph.dongles():
        g.set_type(dongle.spawn, VertexType.BOUNDARY)
    # Ensure that boundaries are connected to exactly one green node and vice versa
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        if g.type(neighbour) == VertexType.X: # Ensure boundary is not connected to an X node
            new_nodes.append(place_node_between(g, VertexType.Z, boundary, neighbour))
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        if g.type(neighbour) == VertexType.Z: # Ensure neighbouring Z spiders are not connected to two boundaries
            neighbour_boundaries = [v for v in g.neighbors(neighbour) if g.type(v) == VertexType.BOUNDARY]
            if len(neighbour_boundaries) > 1:
                new_x = place_node_between(g, VertexType.X, boundary, neighbour)
                new_nodes.append(new_x)
                new_nodes.append(place_node_between(g, VertexType.Z, boundary, new_x))
    z_boundaries = {list(g.neighbors(b))[0] : b for b in boundaries}

    if debug is not None:
        debug['g'] = g
        debug['boundaries'] = boundaries
        debug['z_boundaries'] = z_boundaries
        debug['z_boundaries_types'] = list(map(lambda _v: g.type(_v), z_boundaries.keys()))
        gc = g.clone(ShieldedGraph())
        to_gh(gc)
        debug['gh'] = gc
        debug['graphlike'] = is_graph_like(gc, strict=True)

    # Compute new adjacency
    num_z_boundaries = len(z_boundaries.keys())
    z_internals = list(g.vertex_set().difference(boundaries).difference(z_boundaries.keys()))
    num_z_internals = len(z_internals)

    vertex_forward: Dict[int, int] = dict() # graph vertex to new adjacency
    vertex_backward: Dict[int, int] = dict() # new adjacency to graph vertex
    for i,boundary in enumerate(z_boundaries.keys()):
        vertex_forward[boundary] = i
        vertex_backward[i] = boundary
    for i,internal in enumerate(z_internals):
        vertex_forward[internal] = i + num_z_boundaries
        vertex_backward[i + num_z_boundaries] = internal

    num_spiders = num_z_boundaries + num_z_internals
    adj_matrix = Mat2.zeros(num_spiders, num_spiders) # TODO order pi_2 to the end in adjacency
    for s in g.graph:
        for t in g.graph[s]:
            if g.type(s) != VertexType.BOUNDARY and g.type(t) != VertexType.BOUNDARY:
                adj_matrix[vertex_forward[s],vertex_forward[t]] += 1

    if debug is not None:
        debug['adj_matrix'] = adj_matrix

    m_d = Mat2.zeros(adj_matrix.rows(), adj_matrix.cols() + num_z_boundaries) # TODO add requirement that dongle must be fired / and inputs may not be fired??
    m_d[0:num_z_boundaries,0:num_z_boundaries] = Mat2.id(num_z_boundaries)
    m_d[:,num_z_boundaries:] = adj_matrix
    num_pi_2 = len(list(filter(lambda _v: g.phase(_v) == Fraction(1, 2), g.vertices())))
    m_d[m_d.rows()-num_pi_2:,m_d.rows()-num_pi_2:] = Mat2.id(num_pi_2)

    if debug is not None:
        debug['M_D'] = m_d

    # Compute span of space of valid firing assignments
    sols = m_d.nullspace()
    non_trivial_sols = list(filter(lambda _sol: sum(_sol[:2 * num_z_boundaries]) != 0, sols))
    if debug is not None:
        debug['sols'] = sols
        debug['non_trivial_sols'] = non_trivial_sols

    # Convert firing assignments to pauli webs
    def _convert_to_g_web(v: List[Z2]) -> PauliWeb:
        g_web = PauliWeb(g)

        # Fire all green spiders with full red edges and thus their red neighbours
        for adj_vertex, g_vertex in vertex_backward.items():
            g_type = g.type(g_vertex)
            if g_type == VertexType.Z and v[adj_vertex + num_z_boundaries] == 1:
                for _n in g.neighbors(g_vertex):
                    g_web.add_edge((g_vertex, _n), 'X')

        # Fire all red spiders with full green edges and thus their green neighbours
        for adj_vertex, g_vertex in vertex_backward.items():
            g_type = g.type(g_vertex)
            if g_type == VertexType.X and v[adj_vertex + num_z_boundaries] == 1:
                for _n in g.neighbors(g_vertex):
                    g_web.add_edge((g_vertex, _n), 'Z')

        # Fire all green output edges
        for g_z_boundary, g_boundary in z_boundaries.items():
            adj_z_boundary = vertex_forward[g_z_boundary]
            if v[adj_z_boundary] == 1:
                g_web.add_edge((g_z_boundary, g_boundary), 'Z')

        return g_web

    g_webs = list(map(_convert_to_g_web, non_trivial_sols))
    if debug is not None:
        debug['g_webs'] = g_webs

    def _reduce(g_web: PauliWeb) -> PauliWeb:
        web = PauliWeb(graph)
        done = dict()
        for e,pauli in g_web.half_edges().items():
            left, right = e
            last_left, last_right = right, left
            while left in new_nodes:
                n1, n2 = g.neighbors(left)
                new_left = n1 if n2 == last_left else n2
                last_left = left
                left = new_left
            while right in new_nodes:
                n1, n2 = g.neighbors(right)
                new_right = n1 if n2 == last_right else n2
                last_right = right
                right = new_right

            new_e = left, right
            if new_e not in done:
                done[new_e] = True
                web.add_half_edge(new_e, pauli)

        return web

    return list(map(_reduce, g_webs))
