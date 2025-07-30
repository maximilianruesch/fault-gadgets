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

from typing import List

from .sink import SinkType
from .web import compute_detecting_regions
from .graph import GadgetGraph
from .pauli import PauliWeb, Pauli

def add_sinks_for_all_detecting_regions(dg: GadgetGraph) -> int:
    return add_sinks_for_regions(dg, compute_detecting_regions(dg))

def add_sinks_for_regions(dg: GadgetGraph, regions: List[PauliWeb]) -> int:
    web_index_by_z_edge = dict()
    web_index_by_x_edge = dict()
    for idx, web in enumerate(regions):
        for edge, pauli in web.half_edges().items():
            if pauli == Pauli.Z or pauli == Pauli.Y:
                if edge not in web_index_by_z_edge: web_index_by_z_edge[edge] = []
                web_index_by_z_edge[edge].append(idx)
            if pauli == Pauli.X or pauli == Pauli.Y:
                if edge not in web_index_by_x_edge: web_index_by_x_edge[edge] = []
                web_index_by_x_edge[edge].append(idx)

    unique_z_edge_by_web_index = dict()
    unique_x_edge_by_web_index = dict()
    for edge, indices in web_index_by_z_edge.items():
        if len(indices) == 1:
            unique_z_edge_by_web_index[indices[0]] = edge
    for edge, indices in web_index_by_x_edge.items():
        if len(indices) == 1:
            unique_x_edge_by_web_index[indices[0]] = edge

    webs_without_unique_edge = [
        i for i in range(len(regions))
        if i not in unique_z_edge_by_web_index and i not in unique_x_edge_by_web_index
    ]
    if len(webs_without_unique_edge) > 0:
        raise ValueError("Some webs do not have unique edges!")

    num_sinks_added = 0
    for idx, web in enumerate(regions):
        if idx in unique_z_edge_by_web_index:
            dg.add_sink(unique_z_edge_by_web_index[idx], SinkType.X)
            num_sinks_added += 1
        if idx in unique_x_edge_by_web_index:
            dg.add_sink(unique_x_edge_by_web_index[idx], SinkType.Z)
            num_sinks_added += 1

    return num_sinks_added
