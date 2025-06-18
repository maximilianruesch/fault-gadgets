from pyzx.graph.graph_s import GraphS
import pyzx as zx

from dongle import expand_all_dongles, DongleGraph

from test_dongle.util import assert_graph_equality, dongle_simp

def test_hbox():
    g = GraphS()
    b1 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=0, row=0)
    h = g.add_vertex(zx.VertexType.H_BOX, qubit=0, row=2)
    b2 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=0, row=4)
    g.add_edges([(b1, h), (h, b2)])

    dg = DongleGraph.from_graph(g)
    dg.add_dongle(types=['X'], edge=(b1, h))
    dg.add_dongle(types=['X'], edge=(h, b2))
    expand_all_dongles(dg)

    g2, nodes = dg.realise()
    dongle_simp(g2, nodes)

    assert_graph_equality(g, dg)
