from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, ClassVar, Optional, Tuple

from pyzx import VertexType, EdgeType
from pyzx.editor_actions import match_hadamard_edge
from pyzx.graph.graph_s import GraphS

from .pauli import Pauli, PauliWeb

@dataclass(init=True, frozen=True)
class ExtraIdNode:
    node: int

    def validate(self, adj: Dict[int, Dict[int, any]], web: PauliWeb) -> None:
        v1, v2 = adj[self.node].keys()
        sequence = [web[v1, self.node], web[self.node, v1], web[self.node, v2], web[v2, self.node]]
        if len(set(sequence)) != 1:
            raise AssertionError(f"Invalid ID-nodes {self.node} half edges: {sequence}!")

@dataclass(init=True, frozen=True)
class ExpandedHadamard:
    r1_node: int
    r2_node: int
    r3_node: int
    origin: Optional[int]
    flipped_decomposition: bool

    id_sequence: ClassVar[List[Pauli]] = ['I', 'I', 'I', 'I', 'I', 'I']
    y_sequence: ClassVar[List[Pauli]] = ['Y', 'X', 'X', 'X', 'X', 'Y']
    zx_sequence: ClassVar[List[Pauli]] = ['Z', 'Z', 'Z', 'Y', 'Y', 'X']
    xz_sequence: ClassVar[List[Pauli]] = ['X', 'Y', 'Y', 'Z', 'Z', 'Z']
    zx_h_sequence: ClassVar[List[Pauli]] = ['Z', 'Z', 'Z', 'Y', 'Y', 'X']
    xz_h_sequence: ClassVar[List[Pauli]] = ['X', 'Y', 'Y', 'Z', 'Z', 'Z']

    def _sequence_valid(self, sequence: List[Pauli]) -> bool:
        if sequence == ExpandedHadamard.id_sequence:
            return True

        if self.flipped_decomposition and (
            sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.zx_sequence))
                or sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.xz_sequence))
                or sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.zx_h_sequence))
                or sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.xz_h_sequence))
                or sequence == list(map(lambda s: Pauli.h_flip(s), ExpandedHadamard.y_sequence))
        ):
            return True
        elif sequence == ExpandedHadamard.zx_sequence\
                or sequence == ExpandedHadamard.xz_sequence\
                or sequence == ExpandedHadamard.zx_h_sequence\
                or sequence == ExpandedHadamard.xz_h_sequence\
                or sequence == ExpandedHadamard.y_sequence:
            return True

        return False

    def validate(self, adj: Dict[int, Dict[int, any]], web: PauliWeb) -> None:
        w1, w2, w3 = self.r1_node, self.r2_node, self.r3_node
        w1_left, w1_right = adj[w1].keys()
        l = w1_left if w1_right == w2 else w1_right
        w3_left, w3_right = adj[w3].keys()
        r = w3_right if w3_left == w2 else w3_left

        sequence = [web[w1, l], web[w1, w2], web[w2, w1], web[w2, w3], web[w3, w2], web[w3, r]]
        if not self._sequence_valid(sequence):
            raise AssertionError(f"Invalid H-nodes {str((w1, w2, w3))} half edges: {sequence}!")

class AdditionalNodes:
    extra_id_nodes: List[ExtraIdNode]
    expanded_hadamards: List[ExpandedHadamard]

    def __init__(self, extra_id_nodes: List[ExtraIdNode], expanded_hadamards: List[ExpandedHadamard]):
        self.extra_id_nodes = extra_id_nodes
        self.expanded_hadamards = expanded_hadamards

    @staticmethod
    def empty() -> 'AdditionalNodes':
        return AdditionalNodes([], [])

    def add_extra_id_node(self, node: int):
        self.extra_id_nodes.append(ExtraIdNode(node))

    def add_expanded_hadamard(self, expanded_hadamard: ExpandedHadamard):
        self.expanded_hadamards.append(expanded_hadamard)

    def _remove_extra_id_node(self, adj: Dict[int, Dict[int, any]], web: PauliWeb, id_node: ExtraIdNode):
        v1, v2 = adj[id_node.node].keys()
        web.add_edge((v1, v2), web[v1, id_node.node])
        adj[v1][v2] = True
        adj[v2][v1] = True
        web.remove_edges([(v1, id_node.node), (id_node.node, v2)])
        del adj[v1][id_node.node]
        del adj[id_node.node][v1]
        del adj[id_node.node][v2]
        del adj[v2][id_node.node]

    def _remove_expanded_hadamard(self, adj: Dict[int, Dict[int, any]], web: PauliWeb, hadamard: ExpandedHadamard):
        w1, w2, w3 = hadamard.r1_node, hadamard.r2_node, hadamard.r3_node
        w1_left, w1_right = adj[w1].keys()
        l = w1_left if w1_right == w2 else w1_right
        w3_left, w3_right = adj[w3].keys()
        r = w3_right if w3_left == w2 else w3_left

        if hadamard.origin is not None:
            web.add_half_edge((l, hadamard.origin), web[l, w1])
            web.add_half_edge((hadamard.origin, l), web[l, w1])
            web.add_half_edge((hadamard.origin, r), web[r, w3])
            web.add_half_edge((r, hadamard.origin), web[r, w3])
            if hadamard.origin not in adj: adj[hadamard.origin] = dict()
            adj[l][hadamard.origin] = True
            adj[hadamard.origin][l] = True
            adj[hadamard.origin][r] = True
            adj[r][hadamard.origin] = True
        else:
            web.add_half_edge((l, r), web[l, w1])
            web.add_half_edge((r, l), web[r, w3])
            adj[l][r] = True
            adj[r][l] = True
        web.remove_edges([(l, w1), (w1, w2), (w2, w3), (w3, r)])
        del adj[l][w1]
        del adj[w1][l]
        del adj[w1][w2]
        del adj[w2][w1]
        del adj[w2][w3]
        del adj[w3][w2]
        del adj[w3][r]
        del adj[r][w3]

    def remove_from(self, g: GraphS, web: PauliWeb, validate: bool = False) -> None:
        adj = { v: vs.copy() for v, vs in g.graph.items() }
        for id_node in self.extra_id_nodes:
            if validate: id_node.validate(adj, web)
            self._remove_extra_id_node(adj, web, id_node)
        for hadamard in self.expanded_hadamards:
            if validate: hadamard.validate(adj, web)
            self._remove_expanded_hadamard(adj, web, hadamard)

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

def _euler_expand_edges(g: GraphS, nodes: AdditionalNodes) -> None:
    """
    A cut down version of pyzx.euler_expansion which does not add global scalars and does not prematurely 'merge' spiders
    """
    decomposition_xzx = [VertexType.X, VertexType.Z, VertexType.X]
    decomposition_zxz = [VertexType.Z, VertexType.X, VertexType.Z]

    def _decompose_between(_v1: int, _v2: int, _flip: bool) -> Tuple[int, int, int]:
        # Change decomposition to avoid introducing more X-spiders due to adjacent Z-spider
        pattern = decomposition_xzx if _flip else decomposition_zxz

        _w2 = _place_node_between(g, pattern[1], _v1, _v2)
        g.add_to_phase(_w2, Fraction(1, 2))
        _w1 = _place_node_between(g, pattern[0], _v1, _w2)
        g.add_to_phase(_w1, Fraction(1, 2))
        _w3 = _place_node_between(g, pattern[2], _w2, _v2)
        g.add_to_phase(_w3, Fraction(1, 2))

        return _w1, _w2, _w3

    for v in list(g.vertices()):
        if g.type(v) != VertexType.H_BOX:
            continue

        v1, v2 = g.neighbors(v)
        v1_edge_type = g.edge_type((v1, v))
        v2_edge_type = g.edge_type((v2, v))

        g.remove_vertex(v)
        g.add_edge((v1, v2))

        flip = g.type(v1) == g.type(v2) and g.type(v1) == VertexType.X
        w1, w2, w3 = _decompose_between(v1, v2, flip)
        g.set_edge_type((v1, w1), v1_edge_type)
        g.set_edge_type((w3, v2), v2_edge_type)

        nodes.add_expanded_hadamard(ExpandedHadamard(w1, w2, w3, origin=v, flipped_decomposition=flip))

    for v1, v2 in match_hadamard_edge(g):
        flip = g.type(v1) == g.type(v2) and g.type(v1) == VertexType.Z
        w1, w2, w3 = _decompose_between(v1, v2, flip)
        nodes.add_expanded_hadamard(ExpandedHadamard(w1, w2, w3, origin=None, flipped_decomposition=flip))

def to_red_green_graphlike(g: GraphS) -> AdditionalNodes:
    # Convert all H-edges and Hadamards to red and green spiders
    additional_nodes = AdditionalNodes.empty()
    _euler_expand_edges(g, additional_nodes)

    # Verify that diagram is clifford
    offending_vertices = []
    for v in g.vertices():
        v_type = g.type(v)
        if g.phase(v).denominator > 2 or\
            (v_type != VertexType.Z and v_type != VertexType.X and v_type != VertexType.BOUNDARY):
            offending_vertices.append(v)
    if len(offending_vertices) > 0:
        raise AssertionError(f"Given diagram is not a clifford diagram up to hadamard expansion. The following "
                             f"vertices are either not of type X,Z,BOUNDARY or have a non-clifford "
                             f"phase: {', '.join(map(str, offending_vertices))}")
    offending_edges = [e for e in g.edges() if g.edge_type(e) != EdgeType.SIMPLE]
    if len(offending_edges) > 0:
        raise AssertionError(f"Given diagram is not a clifford diagram up to hadamard expansion. The following "
                             f"edges are not simple edges: {', '.join(map(str, offending_edges))}")

    # Introduce intermediate nodes
    for s, t in list(g.edges()):
        if g.type(s) == g.type(t):
            if g.type(s) == VertexType.BOUNDARY or g.type(s) == VertexType.Z:
                new_type = VertexType.X
            else:
                new_type = VertexType.Z
            additional_nodes.add_extra_id_node(_place_node_between(g, new_type, s, t))

    # Ensure boundaries are not connected to a red spider
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        if g.type(neighbour) == VertexType.X:
            additional_nodes.add_extra_id_node(_place_node_between(g, VertexType.Z, boundary, neighbour))

    # Ensure boundaries are not connected to green spiders with nonzero phase or more than one boundary connection
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        neighbour_boundaries = [v for v in g.neighbors(neighbour) if g.type(v) == VertexType.BOUNDARY]
        if g.phase(neighbour) != 0 or len(neighbour_boundaries) > 1:
            new_x = _place_node_between(g, VertexType.X, boundary, neighbour)
            additional_nodes.add_extra_id_node(new_x)
            additional_nodes.add_extra_id_node(_place_node_between(g, VertexType.Z, boundary, new_x))

    return additional_nodes
