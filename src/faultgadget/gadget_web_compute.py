from typing import Mapping, Iterable, NamedTuple, Dict, Tuple, List

import numpy as np
from galois import GF2

from pyzx import Mat2, VertexType
from . import SinkType
from .web import PauliWeb, to_red_green_graphlike, determine_ordering, create_firing_verification, \
    convert_firing_assignment_to_web, Pauli
from .graph import GadgetGraph, Nodes

ET = Tuple[int, int]

class GadgetPauliWeb(NamedTuple):
    meta_half_edges: Dict[ET, Pauli]
    z_gadget: int
    x_gadgets: List[int]
    z_sinks: List[int]
    x_sinks: List[int]

    def __getitem__(self, key: ET) -> Pauli:
        return self.meta_half_edges.get(key, Pauli.I)

    def __repr__(self):
        return f'GadgetPauliWeb({self.z_gadget}, {self.x_gadgets})'

    def half_edges(self):
        return self.meta_half_edges

    @staticmethod
    def extract(web: PauliWeb, nodes: Nodes, validate: bool = True) -> 'GadgetPauliWeb': # TODO do more validation with debug flag?
        es = web.es.copy()
        z_gadget = None
        x_gadgets = []
        z_sinks = []
        x_sinks = []

        for gadget_id, gadget_nodes in nodes.gadgets.items():
            spawn_dist_pauli = es.pop((gadget_nodes.spawn, gadget_nodes.dist), '')
            es.pop((gadget_nodes.dist, gadget_nodes.spawn), '')

            if spawn_dist_pauli == Pauli.Z:
                if validate and z_gadget is not None:
                    raise RuntimeError("Multiple green highlighted gadgets detected!")
                z_gadget = gadget_id
            elif spawn_dist_pauli == Pauli.X:
                x_gadgets.append(gadget_id)

            for node in nodes.targets[gadget_id]:
                es.pop((gadget_nodes.dist, node), '')
                es.pop((node, gadget_nodes.dist), '')

        for sink_id, sink_nodes in nodes.sinks.items():
            sink_pauli = es.pop((sink_nodes.end, sink_nodes.gate), '')
            es.pop((sink_nodes.gate, sink_nodes.end), '')
            if sink_pauli == Pauli.Z:
                z_sinks.append(sink_id)
            elif sink_pauli == Pauli.X:
                x_sinks.append(sink_id)
            elif validate and sink_pauli == Pauli.Y:
                raise RuntimeError(f"Y-highlight in sink {sink_id} detected!")

        for edge, extra_nodes in nodes.extra_nodes_by_edge.items():
            nodes_on_edge = [edge[0]] + extra_nodes + [edge[1]]

            lr_edge = None
            if (nodes_on_edge[0], nodes_on_edge[1]) in es:
                lr_edge = es[nodes_on_edge[0], nodes_on_edge[1]]
            rl_edge = None
            if (nodes_on_edge[-1], nodes_on_edge[-2]) in es:
                rl_edge = es[nodes_on_edge[-1], nodes_on_edge[-2]]

            for idx in range(len(nodes_on_edge) - 1):
                es.pop((nodes_on_edge[idx], nodes_on_edge[idx + 1]), '')
                es.pop((nodes_on_edge[idx + 1], nodes_on_edge[idx]), '')

            if lr_edge is not None: es[(edge[0], edge[1])] = lr_edge
            if rl_edge is not None: es[(edge[1], edge[0])] = rl_edge

        if validate and z_gadget in x_gadgets:
            raise AssertionError("The gadget of this web may not be highlighted red!")

        return GadgetPauliWeb(es, z_gadget, x_gadgets, z_sinks, x_sinks)

def compute_web_for_gadget(graph: GadgetGraph, gadget_id: int) -> GadgetPauliWeb:
    return compute_webs_for_gadgets(graph, [gadget_id])[gadget_id]

def compute_webs_for_gadgets(graph: GadgetGraph, gadget_ids: Iterable[int]) -> Mapping[int, GadgetPauliWeb]:
    """
    Computes a Pauli web for the given gadget in the graph context.
    A valid web for the gadget is one that features a Z-type edge between the gadgets spawn and distributor.
    """
    g, nodes = graph.realise()

    spawns = [nodes.gadgets[gadget_id].spawn for gadget_id in gadget_ids]
    for spawn in spawns:
        g.set_type(spawn, VertexType.BOUNDARY)

    for sink_nodes in nodes.sinks.values():
        g.set_type(sink_nodes.end, VertexType.BOUNDARY)

    # Computing all webs of all gadgets
    additional_nodes = to_red_green_graphlike(g)
    ordering = determine_ordering(g)

    m_d = GF2(create_firing_verification(g, ordering).data)
    sols_basis_galois = m_d.null_space().transpose()
    sols_basis = Mat2(sols_basis_galois.tolist())

    # A restriction of the solution basis focused on the entries for Z-edges on gadget spawns.
    # Contains one additional entry for restricting X-edges on the gadget to be analyzed.
    # Dimension: (number_gadgets + 1) x (web solution vector count)
    spawn_restricted_basis = []
    for spawn in spawns:
        spawn_restricted_basis.append(sols_basis.data[ordering.ord(list(g.neighbors(spawn))[0])])
    for sink_id, sink in graph.sinks().items():
        offset = 0 if sink.type == SinkType.X else len(ordering.z_boundaries)
        spawn_restricted_basis.append(sols_basis.data[ordering.ord(list(g.neighbors(nodes.sinks[sink_id].end))[0]) + offset])
    spawn_restricted_basis.append([])

    webs = dict()
    for gadget_id in gadget_ids:
        spawn = nodes.gadgets[gadget_id].spawn
        # Replace X constraint only for current gadget spawn
        x_constraint_index = ordering.ord(list(g.neighbors(spawn))[0]) + len(ordering.z_boundaries)
        spawn_restricted_basis[-1] = sols_basis.data[x_constraint_index]

        b = Mat2.unit_vector(len(spawns) + len(graph.sinks()) + 1, spawns.index(spawn))
        basis_sol = Mat2(spawn_restricted_basis).solve(b)
        if basis_sol is None:
           raise AssertionError(f"No valid assignment in basis found for gadget ID {gadget_id}!")
        firing_assignment = np.dot(np.array(sols_basis.data), np.array(basis_sol.data)) % 2

        web = convert_firing_assignment_to_web(g, ordering, firing_assignment.flatten().tolist())
        additional_nodes.remove_from(g, web)
        webs[gadget_id] = GadgetPauliWeb.extract(web, nodes)

    return webs
