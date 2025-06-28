from typing import Tuple, List, Mapping

from pyzx import VertexType
from .sink import SinkType
from .web import PauliWeb, Pauli, compute_detecting_regions
from .graph import GadgetGraph

ET = Tuple[int, int]

def add_all_gadgets(dg: GadgetGraph) -> Mapping[ET, Tuple[int, int, int]]:
    edge_to_gadget_ids = dict()
    for edge in list(dg.edges()):
        # Gadgets on inputs and outputs do not change for rewrites, thus skip
        if dg.type(edge[0]) is VertexType.BOUNDARY or dg.type(edge[1]) is VertexType.BOUNDARY:
            continue

        edge_to_gadget_ids[edge] = dg.add_edge_flip_gadgets(edge)

    return edge_to_gadget_ids

def add_sinks_for_all_detecting_regions(dg: GadgetGraph) -> None:
    add_sinks_for_regions(dg, compute_detecting_regions(dg))

def add_sinks_for_regions(dg: GadgetGraph, regions: List[PauliWeb]) -> None:
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

    for idx, web in enumerate(regions):
        if idx in unique_z_edge_by_web_index:
            dg.add_sink(unique_z_edge_by_web_index[idx], SinkType.X)
        if idx in unique_x_edge_by_web_index:
            dg.add_sink(unique_x_edge_by_web_index[idx], SinkType.Z)
