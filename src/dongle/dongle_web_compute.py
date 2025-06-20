from typing import Mapping, Iterable, NamedTuple, Dict, Tuple, List

import numpy as np

from pyzx import Mat2, VertexType
from . import SinkType
from .web import PauliWeb, to_red_green_graphlike, determine_ordering, create_firing_verification, \
    convert_firing_assignment_to_web, Pauli
from .graph import DongleGraph, Nodes

ET = Tuple[int, int]

class DonglePauliWeb(NamedTuple):
    meta_half_edges: Dict[ET, Pauli]
    z_dongle: int
    x_dongles: List[int]
    z_sinks: List[int]
    x_sinks: List[int]

    def __getitem__(self, key: ET) -> Pauli:
        return self.meta_half_edges.get(key, Pauli.I)

    def __repr__(self):
        return f'DonglePauliWeb({self.z_dongle}, {self.x_dongles})'

    def half_edges(self):
        return self.meta_half_edges

    @staticmethod
    def extract(web: PauliWeb, nodes: Nodes, validate: bool = True) -> 'DonglePauliWeb': # TODO do more validation with debug flag?
        es = web.es.copy()
        z_dongle = None
        x_dongles = []
        z_sinks = []
        x_sinks = []

        for dongle_id, dongle_nodes in nodes.dongles.items():
            spawn_dist_pauli = es.pop((dongle_nodes.spawn, dongle_nodes.dist), '')
            es.pop((dongle_nodes.dist, dongle_nodes.spawn), '')

            if spawn_dist_pauli == Pauli.Z:
                if validate and z_dongle is not None:
                    raise RuntimeError("Multiple green highlighted dongles detected!")
                z_dongle = dongle_id
            elif spawn_dist_pauli == Pauli.X:
                x_dongles.append(dongle_id)

            for node in nodes.targets[dongle_id]:
                es.pop((dongle_nodes.dist, node), '')
                es.pop((node, dongle_nodes.dist), '')

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

            if lr_edge is not None: es[(nodes_on_edge[0], nodes_on_edge[-1])] = lr_edge
            if rl_edge is not None: es[(nodes_on_edge[-1], nodes_on_edge[0])] = rl_edge

        if validate and z_dongle in x_dongles:
            raise AssertionError("The dongle of this web may not be highlighted red!")

        return DonglePauliWeb(es, z_dongle, x_dongles, z_sinks, x_sinks)

def compute_web_for_dongle(graph: DongleGraph, dongle_id: int) -> DonglePauliWeb:
    return compute_webs_for_dongles(graph, [dongle_id])[dongle_id]

def compute_webs_for_dongles(graph: DongleGraph, dongle_ids: Iterable[int]) -> Mapping[int, DonglePauliWeb]:
    """
    Computes a Pauli web for the given dongle in the graph context.
    A valid web for the dongle is one that features a Z-type edge between the dongles spawn and distributor.
    """
    g, nodes = graph.realise()

    dongle_spawns = [nodes.dongles[dongle_id].spawn for dongle_id in dongle_ids]
    for spawn in dongle_spawns:
        g.set_type(spawn, VertexType.BOUNDARY)

    for sink_nodes in nodes.sinks.values():
        g.set_type(sink_nodes.end, VertexType.BOUNDARY)

    # Computing all webs of all dongles
    additional_nodes = to_red_green_graphlike(g)
    ordering = determine_ordering(g)

    m_d = create_firing_verification(g, ordering)
    sols_basis = Mat2(m_d.nullspace()).transpose()

    # A restriction of the solution basis focused on the entries for Z-edges on dongle spawns.
    # Contains one additional entry for restricting X-edges on the dongle to be analyzed.
    # Dimension: (number_dongles + 1) x (web solution vector count)
    spawn_restricted_basis = []
    for spawn in dongle_spawns:
        spawn_restricted_basis.append(sols_basis.data[ordering.ord(list(g.neighbors(spawn))[0])])
    for sink_id, sink in graph.sinks().items():
        offset = 0 if sink.type == SinkType.X else len(ordering.z_boundaries)
        spawn_restricted_basis.append(sols_basis.data[ordering.ord(list(g.neighbors(nodes.sinks[sink_id].end))[0]) + offset])
    spawn_restricted_basis.append([])

    webs = dict()
    for dongle_id in dongle_ids:
        spawn = nodes.dongles[dongle_id].spawn
        # Replace X constraint only for current dongle spawn
        x_constraint_index = ordering.ord(list(g.neighbors(spawn))[0]) + len(ordering.z_boundaries)
        spawn_restricted_basis[-1] = sols_basis.data[x_constraint_index]

        b = Mat2.unit_vector(len(dongle_spawns) + len(graph.sinks()) + 1, dongle_spawns.index(spawn))
        basis_sol = Mat2(spawn_restricted_basis).solve(b)
        if basis_sol is None:
           raise AssertionError(f"No valid assignment in basis found for dongle ID {dongle_id}!")
        firing_assignment = np.dot(np.array(sols_basis.data), np.array(basis_sol.data)) % 2

        web = convert_firing_assignment_to_web(g, ordering, firing_assignment.flatten().tolist())
        additional_nodes.remove_from(g, web)
        dongle_web = DonglePauliWeb.extract(web, nodes)
        webs[dongle_id] = dongle_web

    return webs
