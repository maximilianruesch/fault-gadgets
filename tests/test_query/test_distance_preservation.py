import math
from typing import List, Tuple

import pytest

import pyzx as zx
from faultgadget.query.distancepreserving import is_distance_preserving
from pyzx.graph.graph_s import GraphS

def test_id_spider_simp():
    """
    Simplification of a single spider to an identity wire.
    """
    g1 = GraphS()
    z = g1.add_vertex(zx.VertexType.Z)
    g1.add_edges([
        (g1.add_vertex(zx.VertexType.BOUNDARY), z),
        (z, g1.add_vertex(zx.VertexType.BOUNDARY))
    ])

    g2 = GraphS()
    g2.add_edges([(g2.add_vertex(zx.VertexType.BOUNDARY), g2.add_vertex(zx.VertexType.BOUNDARY))])

    assert is_distance_preserving(g1, g2)

@pytest.mark.parametrize("fan_out", [2, 4, 10, 69])
def test_no_leg_spider_fuse(fan_out):
    """
    Fusing a spider with exactly one leg into its neighbor with a variable number of legs.
    """
    g1 = GraphS()
    bz, z = g1.add_vertex(zx.VertexType.Z), g1.add_vertex(zx.VertexType.Z)
    g1.add_edge((bz, z))
    for i in range(fan_out):
        g1.add_edge((z, g1.add_vertex(zx.VertexType.BOUNDARY)))

    g2 = g1.clone(GraphS())
    g2.remove_vertex(bz)

    assert is_distance_preserving(g1, g2)

def _organize_in_ring(g: GraphS, nodes: List[int], radius: float) -> None:
    n = len(nodes)
    step = 2 * math.pi / n  # angular spacing

    for i, node in enumerate(nodes):
        g.set_qubit(node, radius * math.sin(i * step))
        g.set_row(node, radius * math.cos(i * step))

@pytest.mark.parametrize("ring_size", [3, 4, 5, 6, 7, 8, 9, 10])
def test_collapse_ring(ring_size):
    """
    Collapsing a ring of spiders into a single spider.
    """
    g1 = GraphS()
    b_spiders_2 = [g1.add_vertex(zx.VertexType.BOUNDARY) for _ in range(ring_size)]
    z = g1.add_vertex(zx.VertexType.Z, qubit=0, row=0)
    for i in range(ring_size):
        g1.add_edge((z, b_spiders_2[i]))
    _organize_in_ring(g1, b_spiders_2, radius=3.0)

    g2 = GraphS()
    b_spiders = [g2.add_vertex(zx.VertexType.BOUNDARY) for _ in range(ring_size)]
    z_spiders = [g2.add_vertex(zx.VertexType.Z) for _ in range(ring_size)]
    for i in range(ring_size):
        g2.add_edge((z_spiders[i-1], z_spiders[i]))
        g2.add_edge((z_spiders[i], b_spiders[i]))
    _organize_in_ring(g2, b_spiders, radius=5.0)
    _organize_in_ring(g2, z_spiders, radius=3.0)

    if ring_size <= 5:
        assert is_distance_preserving(g1, g2)
    else:
        assert not is_distance_preserving(g1, g2)

def _add_cat_state(g: GraphS, size: int, qubit: int = 0, row: int = 0) -> Tuple[int, List[int]]:
    z = g.add_vertex(zx.VertexType.Z, qubit=qubit, row=row)
    boundaries = [g.add_vertex(zx.VertexType.BOUNDARY, qubit=qubit + i, row=row + 1) for i in range(size)]
    g.add_edges([(z, b) for b in boundaries])

    return z, boundaries

@pytest.mark.parametrize("n", [2, 3, 4, 5, 7])
def test_cat_state_decomposition(n):
    """
    Expanding a cat state with 2n legs into two cat states with n legs.
    From https://arxiv.org/pdf/2506.17181.
    """
    g1 = GraphS()
    _add_cat_state(g1, size=2*n, qubit=0, row=0)

    g2 = GraphS()
    _, bs1 = _add_cat_state(g2, size=n, qubit=2, row=0)
    _, bs2 = _add_cat_state(g2, size=n, qubit=6, row=0)
    new_bs = [g2.add_vertex(zx.VertexType.BOUNDARY, qubit=i, row=2*(n+1)) for i in range(2*n)]
    for i in range(n):
        g2.set_type(bs1[i], zx.VertexType.Z)
        g2.set_type(bs2[i], zx.VertexType.Z)
        g2.add_edges([(bs1[i], bs2[i]), (bs1[i], new_bs[i]), [bs2[i], new_bs[i + n]]])

    assert is_distance_preserving(g1, g2)
