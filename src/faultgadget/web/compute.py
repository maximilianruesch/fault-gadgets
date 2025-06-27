from typing import List

from pyzx import Mat2
from pyzx.graph.graph_s import GraphS
from .graphlike import to_red_green_graphlike
from .firing_assignments import determine_ordering, create_firing_verification, convert_firing_assignment_to_web

from .pauli import PauliWeb

def compute_webs(graph: GraphS) -> List[PauliWeb]:
    g = graph.clone()

    additional_nodes = to_red_green_graphlike(g)
    ordering = determine_ordering(g)
    m_d = create_firing_verification(g, ordering)

    # Compute span of space of valid firing assignments
    sols = m_d.nullspace()
    webs = list(map(lambda v: convert_firing_assignment_to_web(g, ordering, v), sols))
    for web in webs: additional_nodes.remove_from(g, web)

    return webs

def compute_detecting_regions(graph: GraphS) -> List[PauliWeb]:
    g = graph.clone()

    additional_nodes = to_red_green_graphlike(g)
    ordering = determine_ordering(g)
    m_d = create_firing_verification(g, ordering)

    # Compute basis of valid firing assignment space
    sol_basis = Mat2(m_d.nullspace()).transpose()
    # Search for solutions that do not highlight boundary edges, i.e. detecting regions
    boundary_selected_basis = sol_basis[:len(ordering.z_boundaries) * 2,:]
    boundary_nullspace_vectors = boundary_selected_basis.nullspace()
    # Empty nullspace of boundary edges -> no webs that highlight no boundary edges -> no detecting regions
    if len(boundary_nullspace_vectors) == 0:
        return []

    region_sols = (Mat2(boundary_nullspace_vectors) * sol_basis.transpose()).data
    webs = list(map(lambda v: convert_firing_assignment_to_web(g, ordering, v), region_sols))
    for web in webs: additional_nodes.remove_from(g, web)

    return webs
