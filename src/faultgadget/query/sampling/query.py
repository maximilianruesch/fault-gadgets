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
from typing import Iterator

import numpy as np

from pyzx import VertexType
from pyzx.graph.graph_s import GraphS
from ... import add_all_gadgets, GadgetGraph, add_sinks_for_all_detecting_regions, compute_signatures_for_gadgets, \
    Signature


def sample_signatures(g: GraphS, shots: int, p: float = 0.1) -> Iterator[Signature]:
    """
    Given a ZX diagram as a graph, empirically samples fault signatures under the adversarial edge flip noise model.

    :returns The complete list of detector IDs and the list of randomly sampled fault signatures.
    """
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    add_all_gadgets(gadget_graph)
    id_to_signature = compute_signatures_for_gadgets(gadget_graph)

    boundaries_to_idx = { b: i for i, b in enumerate([v for v in g.vertices() if g.type(v) == VertexType.BOUNDARY])}
    sinks_to_idx = { s: i for i, s in enumerate(gadget_graph.sinks().keys()) }

    signatures = [sig.to_int(boundaries_to_idx, sinks_to_idx) for sig in id_to_signature.values()]
    for _ in range(shots):
        # For adversarial noise models *specifically*, this may be improved leveraging the binomial distribution
        sig_active = np.random.choice(a=[False, True], size=len(signatures), p=[1 - p, p])
        combined_signature = 0
        for i, a in enumerate(sig_active):
            if a:
                combined_signature = combined_signature ^ signatures[i]

        yield combined_signature
