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

from pyzx import Mat2
from pyzx.graph.graph_s import GraphS
from . import to_irreversible_red_green_form, convert_firing_assignment_to_signature
from .red_green import to_red_green_form
from .firing_assignments import determine_ordering, create_firing_verification, convert_firing_assignment_to_web
from .. import Signature
from ..pauli import PauliWeb

def compute_webs(graph: GraphS) -> List[PauliWeb]:
    g = graph.clone()

    additional_nodes = to_red_green_form(g)
    ordering = determine_ordering(g)
    m_d = create_firing_verification(g, ordering)

    # Compute span of space of valid firing assignments
    sols = m_d.nullspace()
    webs = list(map(lambda v: convert_firing_assignment_to_web(g, ordering, v), sols))
    for web in webs: additional_nodes.remove_from(g, web)

    return webs

def compute_detecting_regions(graph: GraphS) -> List[PauliWeb]:
    g = graph.clone()

    additional_nodes = to_red_green_form(g)
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

def compute_stabilisers(graph: GraphS) -> List[PauliWeb]:
    g = graph.clone()

    additional_nodes = to_red_green_form(g)
    ordering = determine_ordering(g)
    m_d = create_firing_verification(g, ordering)

    # Compute basis of valid firing assignment space
    sol_basis = Mat2(m_d.nullspace())
    # Search for solutions that do not highlight boundary edges, i.e. detecting regions
    boundary_selected_basis = sol_basis.transpose()[:len(ordering.z_boundaries) * 2,:]

    pivot_cols = []
    boundary_selected_basis.gauss(pivot_cols=pivot_cols)
    stabilisers = [sol_basis.data[i] for i in pivot_cols]

    webs = list(map(lambda v: convert_firing_assignment_to_web(g, ordering, v), stabilisers))
    for web in webs: additional_nodes.remove_from(g, web)

    return webs

def compute_stabiliser_signatures(graph: GraphS) -> List[Signature]:
    """
    Computes the signatures of all stabilisers of the given graph.
    The returned signatures will naturally not activate any sinks.
    """

    g = graph.clone()

    to_irreversible_red_green_form(g)
    ordering = determine_ordering(g)
    m_d = create_firing_verification(g, ordering)

    # Compute basis of valid firing assignment space
    sol_basis = Mat2(m_d.nullspace())
    # Search for solutions that do not highlight boundary edges, i.e. detecting regions
    boundary_selected_basis = sol_basis.transpose()[:len(ordering.z_boundaries) * 2,:]

    pivot_cols = []
    boundary_selected_basis.gauss(pivot_cols=pivot_cols)
    stabilisers = [sol_basis.data[i] for i in pivot_cols]

    return list(map(lambda v: convert_firing_assignment_to_signature(ordering, v), stabilisers))
