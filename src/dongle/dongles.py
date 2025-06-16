from enum import StrEnum
from typing import List, NamedTuple

class DongleTargetType(StrEnum):
    X = "X"
    Z = "Z"

    def flip(self):
        return DongleTargetType.Z if self == DongleTargetType.X else DongleTargetType.X

class DongleTarget(NamedTuple):
    id: int
    type: DongleTargetType

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"DongleTarget({self.id}, {self.type})"

class Dongle(NamedTuple):
    id: int
    spawn: int
    dist: int
    targets: List[DongleTarget]

    def copy(self) -> 'Dongle':
        return Dongle(self.id, self.spawn, self.dist, [t._replace() for t in self.targets])

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"Dongle#{self.id}({self.spawn}, {self.dist}, {self.targets})"

    def __hash__(self):
        return hash(f"Dongle#{self.id}")
