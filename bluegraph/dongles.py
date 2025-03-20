from enum import IntEnum
from typing import List

from pyzx.graph.graph_s import GraphS

class DongleTargetType(IntEnum):
    X = 1
    Z = 2

class DongleTarget:
    _target_type: DongleTargetType

    def __init__(self, target_type: DongleTargetType):
        self._target_type = target_type

    def get_target_type(self) -> DongleTargetType:
        return self._target_type

    def get_left(self) -> int:
        raise NotImplementedError("Needs to be implemented in a subclass!")

    def get_right(self) -> int:
        raise NotImplementedError("Needs to be implemented in a subclass!")

class XTarget(DongleTarget):
    node: int
    hadamard_left: int
    hadamard_right: int

    def __init__(self, node: int,hadamard_left: int, hadamard_right: int):
        DongleTarget.__init__(self, DongleTargetType.X)
        self.node = node
        self.hadamard_left = hadamard_left
        self.hadamard_right = hadamard_right

    def get_left(self) -> int:
        return self.hadamard_left

    def get_right(self) -> int:
        return self.hadamard_right

class ZTarget(DongleTarget):
    node: int

    def __init__(self, node: int):
        DongleTarget.__init__(self, DongleTargetType.Z)
        self.node = node

    def get_left(self) -> int:
        return self.node

    def get_right(self) -> int:
        return self.node

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