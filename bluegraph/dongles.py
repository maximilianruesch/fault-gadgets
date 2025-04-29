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

class SlimDongle:
    graph: GraphS
    targets: List[DongleTarget]

    def __init__(self, graph: GraphS, targets: List[DongleTarget]):
        self.graph = graph
        self.targets = targets

class Dongle:
    graph: GraphS
    spawn_node: int
    distributor_node: int
    targets: List[DongleTarget]

    def __init__(self, graph: GraphS,
                 spawn_node: int, distributor_node: int, targets: List[DongleTarget]):
        self.graph = graph
        self.spawn_node = spawn_node
        self.distributor_node = distributor_node
        self.targets = targets

    @staticmethod
    def from_slim(slim: SlimDongle, spawn_node: int, distributor_node: int) -> 'Dongle':
        return Dongle(slim.graph, spawn_node, distributor_node, slim.targets)