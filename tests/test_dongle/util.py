from dongle.graph import Nodes, DongleGraph
from pyzx.graph.base import BaseGraph
from pyzx.graph.graph_s import GraphS
from pyzx.hsimplify import from_hypergraph_form
import pyzx as zx

def dongle_simp(g: GraphS, nodes: Nodes) -> None:
    matches = [
        (dongle_nodes.spawn, dongle_nodes.dist, [], nodes.targets[dongle_id])
        for dongle_id, dongle_nodes in nodes.dongles.items()
    ]
    etab, rem_vertices, rem_edges, check_isolated_vertices = zx.rules.bialg(g, matches)
    g.add_edge_table(etab)
    g.remove_edges(rem_edges)
    g.remove_vertices(rem_vertices)
    if check_isolated_vertices: g.remove_isolated_vertices()

    zx.id_simp(g)

def sink_simp(g: GraphS, nodes: Nodes) -> None:
    matches = [(gate, end) for gate, end in nodes.sinks.values()]
    etab, rem_vertices, rem_edges, check_isolated_vertices = zx.rules.spider(g, matches)
    g.add_edge_table(etab)
    g.remove_edges(rem_edges)
    g.remove_vertices(rem_vertices)
    if check_isolated_vertices: g.remove_isolated_vertices()

    zx.id_simp(g)

def assert_dongle_graph_equality(g: BaseGraph, dg: DongleGraph, strict: bool = True) -> None:
    dg_cp, nodes = dg.realise()
    from_hypergraph_form(dg_cp)
    dongle_simp(dg_cp, nodes)
    sink_simp(dg_cp, nodes)

    assert_graph_equality(g, dg_cp, strict=strict)

def assert_graph_equality(g1: BaseGraph, g2: BaseGraph, strict: bool = True) -> None:
    if strict:
        assert g1.vertices() == g2.vertices()
        edges_in_g_not_in_dg = [edge for edge in g1.edges() if g2.edge_type(edge) == 0]
        edges_in_dg_not_in_g = [edge for edge in g2.edges() if g1.edge_type(edge) == 0]
        assert len(edges_in_g_not_in_dg) == 0
        assert len(edges_in_dg_not_in_g) == 0
    else:
        assert zx.compare_tensors(g1, g2) # Takes exponential memory to determine!
