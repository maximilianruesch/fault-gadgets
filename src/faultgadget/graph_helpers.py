from typing import Tuple, List, Mapping

from .sink import SinkType
from .web import compute_detecting_regions
from .graph import GadgetGraph
from .pauli import PauliWeb, Pauli

ET = Tuple[int, int]

def add_all_gadgets(dg: GadgetGraph) -> Mapping[ET, Tuple[int, int, int]]:
    return { edge: dg.add_edge_flip_gadgets(edge) for edge in list(dg.edges()) }

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
