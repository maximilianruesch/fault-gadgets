from enum import StrEnum
from typing import List

from pyzx.graph.graph_s import GraphS

class DongleTargetType(StrEnum):
    X = "X"
    Z = "Z"

    def flip(self):
        return DongleTargetType.Z if self == DongleTargetType.X else DongleTargetType.X

class DongleTarget:
    _id: int
    _type: DongleTargetType

    def __init__(self, _id: int, _type: DongleTargetType):
        self._id = _id
        self._type = _type

    def copy(self) -> 'DongleTarget':
        return DongleTarget(self._id, self._type)

    def get_id(self) -> int:
        return self._id

    def get_type(self) -> DongleTargetType:
        return self._type

    def set_type(self, _type: DongleTargetType) -> None:
        self._type = _type

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"DongleTarget({self._id}, {self._type})"

class Dongle:
    graph: GraphS
    spawn: int
    dist: int
    targets: List[DongleTarget]

    def copy(self) -> 'Dongle':
        return Dongle(self.graph, self.spawn, self.dist, [t.copy() for t in self.targets])

    def __init__(self, graph: GraphS,
                 spawn: int, dist: int, targets: List[DongleTarget]):
        self.graph = graph
        self.spawn = spawn
        self.dist = dist
        self.targets = targets

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"Dongle({self.graph}, {self.spawn}, {self.dist}, {self.targets})"
