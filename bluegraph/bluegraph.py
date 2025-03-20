from enum import IntEnum
from typing import Tuple, Dict, List, Iterable

from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

class DongleType(IntEnum):
    X = 1
    Z = 2
    Y = 3

class Dongle:
    graph: GraphS
    dongle_type: DongleType
    spawn: int
    distributor: int
    targets: List[int]

    def __init__(self, graph: GraphS, dongle_type: DongleType,
                 spawn: int, distributor: int, targets: List[int]):
        self.graph = graph
        self.dongle_type = dongle_type
        self.spawn = spawn
        self.distributor = distributor
        self.targets = targets

class BlueGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._blue: Dict[Tuple[int, int], bool] = dict()
        self._dongles: Dict[int, Dongle] = dict()

    def clone(self):
        cpy = GraphS.clone(self)
        cpy._blue = self._blue.copy()

        return cpy

    def _mark_blue(self, edges: Iterable[Tuple[int, int]]) -> None:
        for (s,t) in edges:
            self._blue[(s,t)] = True
            self._blue[(t,s)] = True

    def _is_blue(self, edge: Tuple[int, int]) -> bool:
        return self._blue[edge]

    def add_dongles(self, edge: Tuple[int, int], repack=False) -> Tuple[Dongle, Dongle]:
        edge_type = self.edge_type(edge)
        if edge_type == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not edge_type == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')

        self.remove_edge(edge)

        x_target, x_dongle = self._instantiate_x_dongle()
        z_target, z_dongle = self._instantiate_z_dongle()

        s,t = edge
        self.add_edges([(s, x_target), (x_target, z_target), (z_target, t)], edgetype=EdgeType.SIMPLE)
        self._mark_blue([(s, x_target), (x_target, z_target), (z_target, t)])

        if repack:
            self.pack_circuit_rows()

        assert self.is_well_formed(), "Circuit is not well formed anymore!"

        return x_dongle, z_dongle

    def _instantiate_x_dongle(self) -> Tuple[int, Dongle]:
        spawn = self.add_vertex(VertexType.X, qubit=-3, row=1.2)
        dist = self.add_vertex(VertexType.Z, qubit=-2, row=1.2)
        x = self.add_vertex(VertexType.X, qubit=-1, row=1.2)
        self.add_edges([(spawn, dist), (dist, x)], edgetype=EdgeType.SIMPLE)
        self._mark_blue([(dist, x)])

        dongle = Dongle(self, DongleType.X, spawn, dist, [x])
        self._dongles[spawn] = dongle

        return x, dongle

    def _instantiate_z_dongle(self) -> Tuple[int, Dongle]:
        spawn = self.add_vertex(VertexType.Z, qubit=-3, row=1.7)
        dist = self.add_vertex(VertexType.X, qubit=-2, row=1.7)
        z = self.add_vertex(VertexType.Z, qubit=-1, row=1.7)
        self.add_edges([(spawn, dist), (dist, z)], edgetype=EdgeType.SIMPLE)
        self._mark_blue([(dist, z)])

        dongle = Dongle(self, DongleType.Y, spawn, dist, [z])
        self._dongles[spawn] = dongle

        return z, dongle

    def _instantiate_y_dongle(self) -> Dongle:
        raise NotImplementedError("Y-Dongles are not yet supported!")
