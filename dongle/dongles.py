from enum import IntEnum
from typing import List

from pyzx.graph.graph_s import GraphS

class DongleTargetType(IntEnum):
    X = 1
    Z = 2

    def flip(self):
        return DongleTargetType.Z if self == DongleTargetType.X else DongleTargetType.X

class DongleTarget:
    _id: int
    _type: DongleTargetType

    def __init__(self, _id: int, _type: DongleTargetType):
        self._id = _id
        self._type = _type

    def get_id(self) -> int:
        return self._id

    def get_type(self) -> DongleTargetType:
        return self._type

    def set_type(self, _type: DongleTargetType) -> None:
        self._type = _type

class Dongle:
    graph: GraphS
    spawn: int
    dist: int
    targets: List[DongleTarget]

    def __init__(self, graph: GraphS,
                 spawn: int, dist: int, targets: List[DongleTarget]):
        self.graph = graph
        self.spawn = spawn
        self.dist = dist
        self.targets = targets
