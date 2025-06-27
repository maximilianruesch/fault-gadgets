import pytest

from faultgadget.graph_helpers import add_all_gadgets, add_sinks_for_all_detecting_regions
from pyzx.graph.graph_s import GraphS
import pyzx as zx

from faultgadget import expand_all_gadgets, GadgetGraph, generate

from test_gadget.util import assert_graph_equality, gadget_simp, assert_gadget_graph_equality

def test_hbox():
    g = GraphS()
    b1 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=0, row=0)
    h = g.add_vertex(zx.VertexType.H_BOX, qubit=0, row=2)
    b2 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=0, row=4)
    g.add_edges([(b1, h), (h, b2)])

    dg = GadgetGraph.from_graph(g)
    dg.add_gadget(types=['X'], edge=(b1, h))
    dg.add_gadget(types=['X'], edge=(h, b2))
    expand_all_gadgets(dg)

    g2, nodes = dg.realise()
    gadget_simp(g2, nodes)

    assert_graph_equality(g, dg)

@pytest.mark.parametrize("qubits,depth", [(2, 2), (3, 3), (4, 7)])
def test_zweb(qubits, depth):
    g = generate.zweb(qubits, depth)

    dg = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(dg)
    add_all_gadgets(dg)
    expand_all_gadgets(dg)

    assert_gadget_graph_equality(g, dg)
