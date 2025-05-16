import pyzx as zx
from dongle import DongleGraph

if __name__ == '__main__':
    g = DongleGraph()
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
    tensor_1 = g.to_tensor()

    g.add_dongles((g_z1, g_z2))
    g.full_instance(h_edges=True)
    print("Did this preserve the matrix?:", zx.compare_tensors(tensor_1, g.to_tensor()))

    zx.draw(g)
