from enum import StrEnum
from typing import Dict, List, Tuple

ET = Tuple[int, int]

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

    @staticmethod
    def from_binary(z_flip: bool, x_flip: bool) -> 'Pauli':
        if z_flip:
            return Pauli.Y if x_flip else Pauli.Z
        else:
            return Pauli.X if x_flip else Pauli.I


class PauliWeb:
    """
    A curated version of pyzx.pauliweb.PauliWeb with additional helper functions.
    """
    def __init__(self):
        self.es: Dict[ET, Pauli] = dict()

    def __getitem__(self, key: ET) -> Pauli:
        return self.es.get(key, Pauli.I)

    def copy(self) -> 'PauliWeb':
        pw = PauliWeb()
        pw.es = self.es.copy()
        return pw

    def add_half_edge(self, v_pair: ET, pauli: Pauli):
        p = self.es.get(v_pair, Pauli.I) * pauli
        if p == Pauli.I: self.es.pop(v_pair,'')
        else: self.es[v_pair] = p

    def add_edge(self, v_pair: ET, pauli: Pauli):
        s, t = v_pair
        self.add_half_edge((s,t), pauli)
        self.add_half_edge((t,s), pauli)

    def remove_edges(self, v_pairs: List[ET]):
        for s, t in v_pairs:
            self.es.pop((s, t), '')
            self.es.pop((t, s), '')

    def vertices(self):
        return set(v for (v,_) in self.es).union(set(v for (_,v) in self.es))

    def half_edges(self) -> Dict[ET, Pauli]:
        return self.es

    def __repr__(self):
        return 'PauliWeb' + str(self.vertices())

    def __mul__(self, other: 'PauliWeb'):
        pw = self.copy()
        for e,p in other.es.items():
            pw.add_half_edge(e, p)
        return pw
