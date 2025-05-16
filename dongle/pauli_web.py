from enum import StrEnum
from typing import Dict, Tuple, List

from dongle.shieldedgraph import ET
from pyzx.graph.graph_s import GraphS
from pyzx.pauliweb import PauliWeb


class Pauli(StrEnum):
    I = "I"
    X = "X"
    Z = "Z"
    Y = "Y"

    def __mul__(self: 'Pauli', other: 'Pauli') -> 'Pauli':
        if self == Pauli.I: return other
        elif other == Pauli.I: return self
        elif self == other: return Pauli.I
        elif self != Pauli.X and other != Pauli.X: return Pauli.X
        elif self != Pauli.Y and other != Pauli.Y: return Pauli.Y
        elif self != Pauli.Z and other != Pauli.Z: return Pauli.Z
        else: raise AssertionError('Should never be reached!')

    def h_flip(self: 'Pauli'):
        if self == Pauli.X: return Pauli.Z
        elif self == Pauli.Z: return Pauli.X
        else: return self

class AdjPauliWeb:
    """
    A curated version of pyzx.pauliweb.PauliWeb with additional helper functions to modify the
    underlying graph adjacency as you go.
    """
    def __init__(self, adj: Dict[int,Dict[int,any]]):
        self.adj = adj
        self.es: Dict[ET, Pauli] = dict()

    def copy(self) -> 'AdjPauliWeb':
        pw = AdjPauliWeb({ v: d.copy() for v, d in self.adj.items() })
        pw.es = self.es.copy()
        return pw

    def neighbors(self, v: int):
        return self.adj[v].keys()

    def remove_id(self, n: int):
        n1, n2 = self.neighbors(n)
        sequence = [
            self.es.get((n1, n), 'I'), self.es.get((n, n1), 'I'),
            self.es.get((n, n2), 'I'), self.es.get((n2, n), 'I')
        ]
        if len(set(sequence)) != 1:
            raise AssertionError(f"Invalid configuration of id-node {n} half edges: {sequence}!")
        self.remove_edges([(n1, n), (n, n2)])
        self.add_edge((n1, n2), sequence[0])

    def remove_hadamard(self, h: Tuple[int, int, int]):
        w1, w2, w3 = h
        w1_left, w1_right = self.neighbors(w1)
        w1_ext = w1_left if w1_right == w2 else w1_right
        w3_left, w3_right = self.neighbors(w3)
        w3_ext = w3_right if w3_left == w2 else w3_left

        sequence = [
            self.es.get((w1_ext, w1), 'I'), self.es.get((w1, w1_ext), 'I'),
            self.es.get((w1, w2), 'I'), self.es.get((w2, w1), 'I'),
            self.es.get((w2, w3), 'I'), self.es.get((w3, w2), 'I'),
            self.es.get((w3, w3_ext), 'I'), self.es.get((w3_ext, w3), 'I')
        ]
        if sequence != ['Z', 'Z', 'Z', 'Z', 'Y', 'Y', 'X', 'X'] \
                and sequence != ['X', 'X', 'Y', 'Y', 'Z', 'Z', 'Z', 'Z'] \
                and sequence != ['Y', 'Y', 'X', 'X', 'X', 'X', 'Y', 'Y'] \
                and sequence != ['I', 'I', 'I', 'I', 'I', 'I', 'I', 'I']:
            raise AssertionError(f"Invalid configuration of H-nodes {str((w1, w2, w3))} half edges: {sequence}!")

        self.remove_edges([(w1_ext, w1), (w1, w2), (w2, w3), (w3, w3_ext)])
        self.add_half_edge((w1_ext, w3_ext), sequence[0])
        self.add_half_edge((w3_ext, w1_ext), sequence[-1])

    def add_half_edge(self, v_pair: ET, pauli: Pauli):
        p = self.es.get(v_pair, Pauli.I) * pauli
        if p == Pauli.I:
            self.es.pop(v_pair,'')
        else:
            self.es[v_pair] = p

    def add_edge(self, v_pair: ET, pauli: Pauli):
        s, t = v_pair
        self.adj[s][t] = True
        self.adj[t][s] = True
        self.add_half_edge((s,t), pauli)
        self.add_half_edge((t,s), pauli)

    def remove_edges(self, v_pairs: List[ET]):
        for s, t in v_pairs:
            del self.adj[s][t]
            del self.adj[t][s]
            self.es.pop((s, t), '')
            self.es.pop((t, s), '')

    def vertices(self):
        return set(v for (v,_) in self.es).union(set(v for (_,v) in self.es))

    def half_edges(self) -> Dict[ET, Pauli]:
        return self.es

    def __repr__(self):
        return 'PauliWeb' + str(self.vertices())

    def __mul__(self, other: 'AdjPauliWeb'):
        pw = self.copy()
        for e,p in other.es.items():
            pw.add_half_edge(e, p)
        return pw

    @staticmethod
    def from_regular_web(web: PauliWeb) -> 'AdjPauliWeb':
        if not isinstance(web.g.clone(), GraphS):
            raise ValueError("Given web has to be associated with a GraphS graph!")

        adj_web = AdjPauliWeb(web.g.clone().graph)
        adj_web.es = {k: Pauli(v) for k, v in web.es.items()}

        return adj_web

    def to_regular_web(self, g) -> PauliWeb:
        web = PauliWeb(g)
        web.es = { k: v.name for k,v in self.es.items() }

        return web
