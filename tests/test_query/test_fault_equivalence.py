import math
from fractions import Fraction
from typing import List, Tuple

import pytest

import pyzx as zx
from faultgadget.query.equivalence import is_fault_equivalent
from pyzx.graph.graph_s import GraphS

def test_id_spider_simp():
    """
    Simplification of a single spider to an identity wire.
    From https://arxiv.org/pdf/2506.17181.
    """
    g1 = GraphS()
    z = g1.add_vertex(zx.VertexType.Z)
    g1.add_edges([
        (g1.add_vertex(zx.VertexType.BOUNDARY), z),
        (z, g1.add_vertex(zx.VertexType.BOUNDARY))
    ])

    g2 = GraphS()
    g2.add_edges([(g2.add_vertex(zx.VertexType.BOUNDARY), g2.add_vertex(zx.VertexType.BOUNDARY))])

    assert is_fault_equivalent(g1, g2)

def test_2_pi_2_fuse():
    """
    Fusing two pi/2 spiders into a single pi spider.
    """
    g1 = GraphS()
    z1, z2 = g1.add_vertex(zx.VertexType.Z, phase=Fraction(1, 2)), g1.add_vertex(zx.VertexType.Z, phase=Fraction(1, 2))
    g1.add_edges([
        (g1.add_vertex(zx.VertexType.BOUNDARY), z1),
        (z1, z2),
        (z2, g1.add_vertex(zx.VertexType.BOUNDARY))
    ])

    g2 = GraphS()
    z = g2.add_vertex(zx.VertexType.Z, phase=1)
    g2.add_edges([
        (g2.add_vertex(zx.VertexType.BOUNDARY), z),
        (z, g2.add_vertex(zx.VertexType.BOUNDARY))
    ])

    assert is_fault_equivalent(g1, g2)

@pytest.mark.parametrize("fan_out", [2, 4, 10, 69])
def test_no_leg_spider_fuse(fan_out):
    """
    Fusing a spider with exactly one leg into its neighbor with a variable number of legs.
    From https://arxiv.org/pdf/2506.17181.
    """
    g1 = GraphS()
    bz, z = g1.add_vertex(zx.VertexType.Z), g1.add_vertex(zx.VertexType.Z)
    g1.add_edge((bz, z))
    for i in range(fan_out):
        g1.add_edge((z, g1.add_vertex(zx.VertexType.BOUNDARY)))

    g2 = g1.clone(GraphS())
    g2.remove_vertex(bz)

    assert is_fault_equivalent(g1, g2)

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
    From https://arxiv.org/pdf/2506.17181 and generalised for ring size > 5.
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
        assert is_fault_equivalent(g1, g2)
    else:
        assert not is_fault_equivalent(g1, g2)

def _add_cat_state(g: GraphS, size: int, qubit: int = 0, row: int = 0) -> Tuple[int, List[int]]:
    z = g.add_vertex(zx.VertexType.Z, qubit=qubit, row=row)
    boundaries = [g.add_vertex(zx.VertexType.BOUNDARY, qubit=qubit + i, row=row + 1) for i in range(size)]
    g.add_edges([(z, b) for b in boundaries])

    return z, boundaries

def _add_cz_layer(g: GraphS, boundaries: List[int]) -> List[int]:
    """
    Adds a layer of CZ gates to the graph, by converting the given boundaries to Z-spiders.
    Let n = boundaries / 2, then boundaries[i] will be connected to boundaries[i+n].
    :returns The new boundaries
    """
    n = len(boundaries) // 2
    new_bs = [g.add_vertex(zx.VertexType.BOUNDARY, qubit=i, row=2 * (n + 1)) for i in range(2 * n)]
    for i in range(n):
        g.set_type(boundaries[i], zx.VertexType.Z)
        g.set_type(boundaries[i + n], zx.VertexType.Z)
        g.add_edges([
            (boundaries[i], boundaries[i + n]),
            (boundaries[i], new_bs[i]),
            (boundaries[i], new_bs[i + n]),
        ])

    return new_bs

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
    _add_cz_layer(g2, [*bs1, *bs2])

    assert is_fault_equivalent(g1, g2, quiet=False)

@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_cat_state_decomposition_in_context(n):
    """
    Expanding a cat state with 2n legs into two cat states with n legs, in a CZ context that forms new detecting
    regions with the expanded states.
    Based on https://arxiv.org/pdf/2506.17181.
    """

    g1 = GraphS()
    _, bs = _add_cat_state(g1, size=2 * n, qubit=0, row=0)
    _add_cz_layer(g1, bs)

    g2 = GraphS()
    _, bs1 = _add_cat_state(g2, size=n, qubit=2, row=0)
    _, bs2 = _add_cat_state(g2, size=n, qubit=6, row=0)
    new_bs = _add_cz_layer(g2, [*bs1, *bs2])
    _add_cz_layer(g2, new_bs)

    assert is_fault_equivalent(g1, g2, quiet=False)
