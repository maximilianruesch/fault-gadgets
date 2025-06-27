from enum import StrEnum
from typing import List, NamedTuple

class TargetType(StrEnum):
    X = "X"
    Z = "Z"

    def flip(self):
        return TargetType.Z if self == TargetType.X else TargetType.X

class Target(NamedTuple):
    id: int
    type: TargetType

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"Target({self.id}, {self.type})"

class Gadget(NamedTuple):
    id: int
    targets: List[Target]

    def copy(self) -> 'Gadget':
        return Gadget(self.id, self.targets.copy())

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"Gadget#{self.id}({self.targets})"

    def __hash__(self):
        return hash(f"Gadget#{self.id}")
