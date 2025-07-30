import pytest

from conftest import longrun

from pyzx.editor_actions import match_hadamard_edge
from pyzx.hrules import had_edge_to_hbox
from faultgadget import expand_all_gadgets, wrap_adversarial_edge_flip_noise, GadgetGraph
import pyzx as zx
from test_gadget.util import assert_gadget_graph_equality

@pytest.mark.parametrize("qubits,depth", [(2, 2), (4, 5)])
def test_cnot(qubits, depth):
    g = zx.generate.cnots(qubits, depth)
    zx.id_simp(g)

    dg, _ = wrap_adversarial_edge_flip_noise(g)
    expand_all_gadgets(dg)

    assert_gadget_graph_equality(g, dg)

@pytest.mark.parametrize("qubits,depth", [(3, 3), (4, 7), (9, 9), (12, 12)])
def test_clifford(qubits, depth):
    g = zx.generate.cliffords(qubits, depth)
    zx.id_simp(g)

    dg = GadgetGraph.from_graph(g)
    for e in match_hadamard_edge(dg):
        had_edge_to_hbox(dg, e)
    wrap_adversarial_edge_flip_noise(dg)
    expand_all_gadgets(dg)

    assert_gadget_graph_equality(g, dg)

@longrun
@pytest.mark.parametrize("qubits,depth", [(10, 50)])
def test_clifford_huge(qubits, depth):
    g = zx.generate.cliffords(qubits, depth)
    zx.id_simp(g)

    dg = GadgetGraph.from_graph(g)
    for e in match_hadamard_edge(dg):
        had_edge_to_hbox(dg, e)
    wrap_adversarial_edge_flip_noise(dg)
    expand_all_gadgets(dg)

    assert_gadget_graph_equality(g, dg)
