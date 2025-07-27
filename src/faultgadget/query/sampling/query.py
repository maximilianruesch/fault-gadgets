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
from typing import Dict, Iterator

import numpy as np

from pyzx.graph.graph_s import GraphS
from ... import add_all_gadgets, GadgetGraph, add_sinks_for_all_detecting_regions, compute_signatures_for_gadgets, \
    Signature
from ...pauli import Pauli


def sample_signatures(g: GraphS, shots: int, p: float = 0.1) -> Iterator[Signature]:
    """
    Given a ZX diagram as a graph, empirically samples fault signatures under the adversarial edge flip noise model.

    :returns The complete list of detector IDs and the list of randomly sampled fault signatures.
    """
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    add_all_gadgets(gadget_graph)
    id_to_signature = compute_signatures_for_gadgets(gadget_graph)

    def combine_signatures(sig1: Signature, sig2: Signature) -> Signature:
        boundaries: Dict[int, Pauli] = defaultdict(lambda: Pauli.I)
        sinks: Dict[int, bool] = defaultdict(lambda: False)

        boundaries1 = set(sig1.boundaries)
        boundaries2 = set(sig2.boundaries)
        for b in boundaries1.intersection(boundaries2):
            boundaries[b] = sig1.boundaries[b] * sig2.boundaries[b]
        for b in boundaries1.difference(boundaries2):
            boundaries[b] = sig1.boundaries[b]
        for b in boundaries2.difference(boundaries1):
            boundaries[b] = sig2.boundaries[b]

        for s, active in sig1.sinks.items():
            sinks[s] = active ^ (sig2.sinks.get(s) or False)
        for s, active in sig2.sinks.items():
            sinks[s] = active ^ (sig1.sinks.get(s) or False)

        return Signature(boundaries, sinks)

    for sig_active in np.random.choice(a=[False, True], size=(shots, len(id_to_signature)), p=[1 - p, p]):
        combined_signature = Signature(dict(), dict())
        for i, a in enumerate(sig_active):
            if a:
                combined_signature = combine_signatures(combined_signature, id_to_signature[i])

        yield combined_signature
