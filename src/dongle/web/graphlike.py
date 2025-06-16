from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Dict, List, ClassVar

from pyzx import VertexType, EdgeType
from pyzx.editor_actions import match_hadamard_edge
from pyzx.graph.graph_s import GraphS
from pyzx.hsimplify import hadamard_simp

from .pauli import Pauli, PauliWeb

@dataclass(init=True)
class ExtraIdNode:
    l_node: int
    node: int
    r_node: int

    def validate(self, web: PauliWeb) -> None:
        sequence = [web[self.l_node, self.node], web[self.node, self.l_node],
                    web[self.node, self.r_node], web[self.r_node, self.node]]
        if len(set(sequence)) != 1:
            raise AssertionError(f"Invalid ID-nodes {self.node} half edges: {sequence}!")

@dataclass(init=True)
class ExpandedHadamard:
    l_node: int
    r1_node: int
    r2_node: int
    r3_node: int
    r_node: int
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

    def validate(self, web: PauliWeb) -> None:
        l, w1, w2, w3, r = self.l_node, self.r1_node, self.r2_node, self.r3_node, self.r_node
        sequence = [web[l, w1], web[w1, l], web[w1, w2], web[w2, w1], web[w2, w3], web[w3, w2], web[w3, r], web[r, w3]]
        if not self._sequence_valid(sequence):
            raise AssertionError(f"Invalid H-nodes {str((w1, w2, w3))} half edges: {sequence}!")

class AdditionalNodes:
    extra_id_nodes: Dict[int, ExtraIdNode]
    expanded_hadamards_left: Dict[int, ExpandedHadamard]
    expanded_hadamards_right: Dict[int, ExpandedHadamard]

    def __init__(self, extra_id_nodes: List[ExtraIdNode], expanded_hadamards: List[ExpandedHadamard]):
        self.extra_id_nodes = { id_node.node: id_node for id_node in extra_id_nodes }
        self.expanded_hadamards_left = { hadamard.r1_node: hadamard for hadamard in expanded_hadamards }
        self.expanded_hadamards_right = { hadamard.r3_node: hadamard for hadamard in expanded_hadamards }

    def copy(self) -> 'AdditionalNodes':
        return AdditionalNodes(
            [replace(id_node) for id_node in self.extra_id_nodes.values()],
            [replace(hadamard) for hadamard in self.expanded_hadamards_left.values()]
        )

    def _refer_neighbors(self, left_neighbor: int, right_neighbor: int) -> None:
        if left_neighbor in self.extra_id_nodes:
            self.extra_id_nodes[left_neighbor].r_node = right_neighbor
        if left_neighbor in self.expanded_hadamards_right:
            self.expanded_hadamards_right[left_neighbor].r_node = right_neighbor

        if right_neighbor in self.extra_id_nodes:
            self.extra_id_nodes[right_neighbor].l_node = left_neighbor
        if right_neighbor in self.expanded_hadamards_left:
            self.expanded_hadamards_left[right_neighbor].l_node = left_neighbor

    def add_extra_id_node(self, l_node: int, node: int, r_node: int):
        self.extra_id_nodes[node] = ExtraIdNode(l_node, node, r_node)
        self._refer_neighbors(l_node, node)
        self._refer_neighbors(node, r_node)

    def _remove_extra_id_node(self, web: PauliWeb, id_node: ExtraIdNode):
        web.add_edge((id_node.l_node, id_node.r_node), web[id_node.l_node, id_node.node])
        web.remove_edges([(id_node.l_node, id_node.node), (id_node.node, id_node.r_node)])
        self._refer_neighbors(id_node.l_node, id_node.r_node)

    def _remove_expanded_hadamard(self, web: PauliWeb, hadamard: ExpandedHadamard):
        l, w1, w2, w3, r = hadamard.l_node, hadamard.r1_node, hadamard.r2_node, hadamard.r3_node, hadamard.r_node
        web.add_half_edge((l, r), web[l, w1])
        web.add_half_edge((r, l), web[r, w3])
        web.remove_edges([(l, w1), (w1, w2), (w2, w3), (w3, r)])
        self._refer_neighbors(l, r)

    def remove_from(self, web: PauliWeb, validate: bool = False) -> None:
        cpy = self.copy()
        for id_node in cpy.extra_id_nodes.values():
            if validate: id_node.validate(web)
            cpy._remove_extra_id_node(web, id_node)
        for hadamard in cpy.expanded_hadamards_left.values():
            if validate: hadamard.validate(web)
            cpy._remove_expanded_hadamard(web, hadamard)

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

        expanded_edges.append(ExpandedHadamard(v1, w1, w2, w3, v2, flipped_decomposition=flip))

    return expanded_edges

def to_red_green_graphlike(g: GraphS) -> AdditionalNodes:
    # Convert all H-edges and Hadamards to red and green spiders
    hadamard_simp(g, quiet=True)
    additional_nodes = AdditionalNodes(extra_id_nodes=[], expanded_hadamards=_euler_expand_edges(g))

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
            additional_nodes.add_extra_id_node(s, _place_node_between(g, new_type, s, t), t)

    # Ensure boundaries are not connected to a red spider
    boundaries = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        if g.type(neighbour) == VertexType.X:
            additional_nodes.add_extra_id_node(boundary, _place_node_between(g, VertexType.Z, boundary, neighbour), neighbour)

    # Ensure boundaries are not connected to green spiders with nonzero phase or more than one boundary connection
    for boundary in boundaries:
        neighbour = list(g.neighbors(boundary))[0]
        neighbour_boundaries = [v for v in g.neighbors(neighbour) if g.type(v) == VertexType.BOUNDARY]
        if g.phase(neighbour) != 0 or len(neighbour_boundaries) > 1:
            new_x = _place_node_between(g, VertexType.X, boundary, neighbour)
            additional_nodes.add_extra_id_node(boundary, new_x, neighbour)
            additional_nodes.add_extra_id_node(boundary,  _place_node_between(g, VertexType.Z, boundary, new_x), new_x)

    return additional_nodes
