import pytest

from conftest import longrun
from dongle.graph_helpers import add_all_dongles

from pyzx.editor_actions import match_hadamard_edge
from pyzx.hrules import had_edge_to_hbox
from dongle import expand_all_dongles, DongleGraph
import pyzx as zx
from test_dongle.util import assert_dongle_graph_equality

@pytest.mark.parametrize("qubits,depth", [(2, 2), (4, 5)])
def test_cnot(qubits, depth):
    g = zx.generate.cnots(qubits, depth)
    zx.id_simp(g)

    dg = DongleGraph.from_graph(g)
    add_all_dongles(dg)
    expand_all_dongles(dg)

    assert_dongle_graph_equality(g, dg)

@pytest.mark.parametrize("qubits,depth", [(3, 3), (4, 7), (9, 9), (12, 12)])
def test_clifford(qubits, depth):
    g = zx.generate.cliffords(qubits, depth)
    zx.id_simp(g)

    dg = DongleGraph.from_graph(g)
    for e in match_hadamard_edge(dg):
        had_edge_to_hbox(dg, e)
    add_all_dongles(dg)
    expand_all_dongles(dg)

    assert_dongle_graph_equality(g, dg)

@longrun
@pytest.mark.parametrize("qubits,depth", [(10, 50)])
def test_clifford_huge(qubits, depth):
    g = zx.generate.cliffords(qubits, depth)
    zx.id_simp(g)

    dg = DongleGraph.from_graph(g)
    for e in match_hadamard_edge(dg):
        had_edge_to_hbox(dg, e)
    add_all_dongles(dg)
    expand_all_dongles(dg)

    assert_dongle_graph_equality(g, dg)
