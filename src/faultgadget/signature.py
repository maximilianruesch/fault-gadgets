# Copyright 2025 Maximilian Rüsch
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import defaultdict
from typing import Mapping, Iterable, Tuple, NamedTuple, Dict

from pyzx import VertexType
from .gadget import TargetType
from .graph import GadgetGraph
from .pauli import Pauli

ET = Tuple[int, int]

class Signature(NamedTuple):
    boundaries: Mapping[int, Pauli]
    sinks: Mapping[int, bool]

    def is_trivial(self) -> bool:
        return len(self.boundaries) == 0 and len(self.sinks) == 0

def gadgets_to_signatures(g: GadgetGraph, gadget_ids: Iterable[int]) -> Mapping[int, Signature]:
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

        signatures[gadget_id] = Signature(boundaries, sinks)

    return signatures
