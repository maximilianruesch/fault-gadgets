from collections import defaultdict
from typing import Mapping, Iterable, Tuple, NamedTuple, Dict

from pyzx import VertexType
from .gadget import TargetType
from .graph import GadgetGraph
from .pauli import Pauli

ET = Tuple[int, int]

type Signature = Mapping[int, Pauli]

class GadgetSignature(NamedTuple):
    boundaries: Mapping[int, Pauli]
    sinks: Mapping[int, bool]

def gadgets_to_signatures(g: GadgetGraph, gadget_ids: Iterable[int]) -> Mapping[int, GadgetSignature]:
    b_vertices = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]

    signatures = dict()
    for gadget_id in gadget_ids:
        gadget = g.gadgets()[gadget_id]

        boundaries: Dict[int, Pauli] = defaultdict(lambda: Pauli.I)
        sinks: Dict[int, bool] = defaultdict(lambda: False)
        for target in gadget.targets:
            on_edge, sink_id = g.on_edge(target.id), g.in_sink(target.id)
            if on_edge is not None:
                boundary = on_edge[0] if on_edge[0] in b_vertices else on_edge[1] if on_edge[1] in b_vertices else None
                if boundary is not None:
                    boundaries[boundary] *= Pauli.Z if target.type == TargetType.Z else Pauli.X
            elif sink_id is not None:
                sinks[sink_id] = True

        signatures[gadget_id] = GadgetSignature(boundaries, sinks)

    return signatures
