from enum import IntEnum
from typing import List

from pyzx.graph.graph_s import GraphS

class DongleTargetType(IntEnum):
    X = 1
    Z = 2

class DongleTarget:
    _id: int
    _target_type: DongleTargetType

    def __init__(self, _id: int, target_type: DongleTargetType):
        self._id = _id
        self._target_type = target_type

    def get_id(self) -> int:
        return self._id

    def get_target_type(self) -> DongleTargetType:
        return self._target_type

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