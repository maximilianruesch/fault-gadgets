import pyzx as zx
from bluegraph import BlueGraph

if __name__ == '__main__':
    g = BlueGraph()
    g_b1 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=0, row=0)
    g_b2 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=1, row=0)
    g_b3 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=0, row=3)
    g_b4 = g.add_vertex(zx.VertexType.BOUNDARY, qubit=1, row=3)

    g_z1 = g.add_vertex(zx.VertexType.Z, qubit=0, row=1)
    g_z2 = g.add_vertex(zx.VertexType.Z, qubit=0, row=2)
    g_z3 = g.add_vertex(zx.VertexType.Z, qubit=1, row=1)
    g_z4 = g.add_vertex(zx.VertexType.Z, qubit=1, row=2)

    g.add_edges([
        (g_b1, g_z1), (g_z1, g_z2), (g_z2, g_b3),
        (g_b2, g_z3), (g_z3, g_z4), (g_z4, g_b4),
        (g_z1,g_z3), (g_z2, g_z4)
    ], edgetype=zx.EdgeType.SIMPLE)

    g.auto_detect_io()
    zx.draw(g)

    g.add_dongles((g_z1, g_z2))

    zx.draw(g)
