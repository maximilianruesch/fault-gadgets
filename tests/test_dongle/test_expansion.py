import pytest

from pyzx import compare_tensors, id_simp, bialg_simp
from pyzx.graph.base import BaseGraph
from pyzx.hsimplify import from_hypergraph_form

from pyzx.editor_actions import match_hadamard_edge
from pyzx.hrules import had_edge_to_hbox
from dongle import expand_all_dongles, DongleGraph
import pyzx as zx

@pytest.fixture
def verbosity_level(request):
    return request.config.option.verbose

def _dongle_simp(dg: DongleGraph) -> None:
    bialg_simp(dg)
    id_simp(dg)

    pass

def _assert_circuit_equality(g: BaseGraph, dg: DongleGraph, verbosity_level) -> None:
    g_tensor = zx.tensorfy(g, preserve_scalar=False)

    dg_cp = dg.clone(DongleGraph())
    dg_cp.realise_all_targets()
    dg_cp.reassign_dongle_positions()
    from_hypergraph_form(dg_cp)

    num_v, num_e = dg_cp.num_vertices(), dg_cp.num_edges()
    _dongle_simp(dg_cp)
    if verbosity_level > 1:
        print(f"Reduced dongle graph from {num_v}:{num_e} to {dg_cp.num_vertices()}:{dg_cp.num_edges()}")
    dg_tensor = zx.tensorfy(dg_cp, preserve_scalar=False)

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
    for e in match_hadamard_edge(g):
        had_edge_to_hbox(g, e)

    dg = DongleGraph.from_graph(g)
    dg.add_all_dongles()
    expand_all_dongles(dg)

    _assert_circuit_equality(g, dg, verbosity_level=verbosity_level)
