from typing import Mapping, List, Iterable, Tuple, NamedTuple

from pyzx import VertexType
from ..gadget import TargetType
from ..graph import GadgetGraph
from ..web import Pauli

ET = Tuple[int, int]

class Signature(NamedTuple):
    boundaries: List[Pauli]
    sinks: List[bool]

def gadgets_to_signatures(g: GadgetGraph, gadget_ids: Iterable[int],
                          boundaries_to_idx: Mapping[ET, int], sink_id_to_idx: Mapping[int, int]) -> Mapping[int, Signature]:
    b_vertices = [v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY]
    if len(b_vertices) != len(boundaries_to_idx):
        raise ValueError(f'Number of boundaries do not match the provided index mappings: {len(b_vertices)} vs. {len(boundaries_to_idx)}!')
    if len(g.sinks()) is not len(sink_id_to_idx):
        raise ValueError(f'Number of sinks do not match the provided index mappings: {len(g.sinks())} vs. {len(sink_id_to_idx)}!')

    signatures = dict()
    for gadget_id in gadget_ids:
        gadget = g.gadgets()[gadget_id]

        boundaries: List[Pauli] = [Pauli.I for _ in range(len(b_vertices))]
        sinks: List[bool] = [False for _ in range(len(g.sinks()))]
        for target in gadget.targets:
            on_edge, sink_id = g.on_edge(target.id), g.in_sink(target.id)
            if on_edge is not None and on_edge in boundaries_to_idx:
                boundaries[boundaries_to_idx[on_edge]] *= Pauli.Z if target.type == TargetType.Z else Pauli.X
            elif sink_id is not None:
                sinks[sink_id_to_idx[sink_id]] = True

        signatures[gadget_id] = Signature(boundaries, sinks)

    return signatures
