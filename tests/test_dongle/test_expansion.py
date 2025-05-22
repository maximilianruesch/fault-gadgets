import random

import pytest

from pyzx import compare_tensors, full_reduce, VertexType
from pyzx.graph.base import BaseGraph
from pyzx.hsimplify import from_hypergraph_form

random.seed(50)

from pyzx.editor_actions import match_hadamard_edge
from pyzx.hrules import had_edge_to_hbox
from dongle import expand_all_dongles, DongleGraph
import pyzx as zx

@pytest.fixture
def verbosity_level(request):
    return request.config.option.verbose

def _assert_circuit_equality(g: BaseGraph, dg: DongleGraph, verbosity_level) -> None:
    g_cp = g.clone()
    g_tensor = zx.tensorfy(g_cp)

    dg_cp = dg.clone(DongleGraph())
    dg_cp.realise_all_targets()
    dg_cp.reassign_dongle_positions()
    from_hypergraph_form(dg_cp)

    num_v, num_e = dg_cp.num_vertices(), dg_cp.num_edges()
    full_reduce(dg_cp)
    if verbosity_level > 1:
        print(f"Reduced dongle graph from {num_v}:{num_e} to {dg_cp.num_vertices()}:{dg_cp.num_edges()}")
    dg_tensor = zx.tensorfy(dg_cp)

    assert compare_tensors(g_tensor, dg_tensor, preserve_scalar=False)

@pytest.mark.parametrize("qubits,depth", [(2, 2), (4, 5)])
def test_cnot(qubits, depth, verbosity_level):
    g = zx.generate.cnots(qubits, depth)
    zx.id_simp(g)

    dg = DongleGraph.from_graph(g)
    dg.add_all_dongles()
    expand_all_dongles(dg)

    _assert_circuit_equality(g, dg, verbosity_level=verbosity_level)

@pytest.mark.parametrize("qubits,depth", [(3, 3), (4, 7), (9, 9)])
def test_clifford(qubits, depth, verbosity_level):
    g = zx.generate.cliffords(qubits, depth)
    zx.clifford_simp(g, quiet=True)
    g.normalize()
    for e in match_hadamard_edge(g):
        had_edge_to_hbox(g, e)

    dg = DongleGraph.from_graph(g)
    dg.add_all_dongles()
    expand_all_dongles(dg)

    _assert_circuit_equality(g, dg, verbosity_level=verbosity_level)
