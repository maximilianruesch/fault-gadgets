from typing import Mapping, Iterable

import numpy as np

from pyzx import Mat2, VertexType
from .web import PauliWeb, to_red_green_graphlike, determine_ordering, create_firing_verification, \
    convert_firing_assignment_to_web
from .graph import DongleGraph

def compute_web_for_dongle(graph: DongleGraph, dongle_id: int) -> PauliWeb:
    return compute_webs_for_dongles(graph, [dongle_id])[dongle_id]

def compute_webs_for_dongles(graph: DongleGraph, dongle_ids: Iterable[int]) -> Mapping[int, PauliWeb]:
    """
    Computes a Pauli web for the given dongle in the graph context.
    A valid web for the dongle is one that features a Z-type edge between the dongles spawn and distributor.
    """
    g = graph.clone(DongleGraph())
    g.realise_all_targets()

    dongle_spawns = [g.dongles()[dongle_id].spawn for dongle_id in dongle_ids]
    for spawn in dongle_spawns:
        g.set_type(spawn, VertexType.BOUNDARY)

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
    spawn_restricted_basis.append([])

    webs = dict()
    for dongle_id in dongle_ids:
        dongle = g.dongles()[dongle_id]
        # Replace X constraint only for current dongle spawn
        x_constraint_index = ordering.ord(list(g.neighbors(dongle.spawn))[0]) + len(ordering.z_boundaries)
        spawn_restricted_basis[-1] = sols_basis.data[x_constraint_index]

        b = Mat2.unit_vector(len(dongle_spawns) + 1, dongle_spawns.index(dongle.spawn))
        basis_sol = Mat2(spawn_restricted_basis).solve(b)
        if basis_sol is None:
           raise AssertionError(f"No valid assignment in basis found for {dongle}!")
        firing_assignment = np.dot(np.array(sols_basis.data), np.array(basis_sol.data)) % 2

        web = convert_firing_assignment_to_web(g, ordering, firing_assignment.flatten().tolist())
        additional_nodes.remove_from(web)
        webs[dongle_id] = web

    return webs
