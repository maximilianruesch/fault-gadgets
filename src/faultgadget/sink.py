from enum import StrEnum
from typing import NamedTuple

class SinkType(StrEnum):
    X = "X"
    Z = "Z"

class Sink(NamedTuple):
    id: int
    type: SinkType

    def __repr__(self):
        return self.__str__()

    def __str__(self) -> str:
        return f"Sink({self.id}, {self.type})"
