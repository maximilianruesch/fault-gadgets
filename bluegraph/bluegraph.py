from typing import Tuple, Dict, Iterable, Literal

from .dongles import Dongle, XTarget, ZTarget, DongleTarget, DongleTargetType
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

class BlueGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._blue: Dict[Tuple[int, int], bool] = dict()
        self._dongles: Dict[int, Dongle] = dict()

    def clone(self):
        cpy = GraphS.clone(self)
        cpy._blue = self._blue.copy()
        cpy._dongles = self._dongles.copy()

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

        s,t = edge

        z_dongle, z_left, z_right = self._z_dongle()
        x_dongle, x_left, x_right = self._x_dongle()
        y_dongle, y_left, y_right = self._y_dongle()

        blue_edges = [(s, z_left), (z_right, x_left), (x_right, y_left), (y_right, t)]
        self.add_edges(blue_edges, edgetype=EdgeType.SIMPLE)
        self._mark_blue(blue_edges)

        if repack:
            self.pack_circuit_rows()

        assert self.is_well_formed(), "Circuit is not well formed anymore!"

        return x_dongle, z_dongle

    def _x_dongle(self) -> Tuple[Dongle, int, int]:
        dongle = self._instantiate_dongle(types=['X'])
        return dongle, dongle.targets[0].get_left(), dongle.targets[0].get_right()

    def _z_dongle(self) -> Tuple[Dongle, int, int]:
        dongle = self._instantiate_dongle(types=['Z'])
        return dongle, dongle.targets[0].get_left(), dongle.targets[0].get_right()

    def _y_dongle(self) -> Tuple[Dongle, int, int]:
        dongle = self._instantiate_dongle(types=['Y'])
        return dongle, dongle.targets[0].get_left(), dongle.targets[1].get_right()

    def _instantiate_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']]):
        spawn = self.add_vertex(VertexType.Z, qubit=-4, row=1.2)
        dist = self.add_vertex(VertexType.X, qubit=-3, row=1.2)

        self.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)
        blue_edges = [(spawn, dist)]
        targets = []

        def _x_target(local_distributor: int) -> XTarget:
            hadamard_left = self.add_vertex(VertexType.H_BOX, qubit=-1, row=1.7)
            node = self.add_vertex(VertexType.Z, qubit=-1, row=1.8)
            hadamard_right = self.add_vertex(VertexType.H_BOX, qubit=-1, row=1.9)
            blue_edges.extend([
                (local_distributor, node),
                (hadamard_left, node),
                (node, hadamard_right),
            ])
            return XTarget(node, hadamard_left, hadamard_right)

        def _z_target(local_distributor: int) -> ZTarget:
            node = self.add_vertex(VertexType.Z, qubit=-1, row=1.6)
            blue_edges.append((local_distributor, node))
            return ZTarget(node)

        for target_type in types:
            if target_type == 'X':
                targets.append(_x_target(dist))
            elif target_type == 'Z':
                targets.append(_z_target(dist))
            else:
                local_dist = self.add_vertex(VertexType.X, qubit=-2, row=1.5)
                z_target = _z_target(local_dist)
                x_target = _x_target(local_dist)
                blue_edges.extend([
                    (dist, local_dist),
                    (local_dist, z_target.node),
                    (local_dist, x_target.node),
                    (z_target.node, x_target.hadamard_left)
                ])
                targets.extend([z_target, x_target])

        self.add_edges(blue_edges, edgetype=EdgeType.SIMPLE)
        self._mark_blue(blue_edges)
        dongle = Dongle(self, spawn, dist, targets)
        self._dongles[spawn] = dongle

        return dongle

    def push_target(self, target: DongleTarget, gateway: int) -> None:
        """ Push the target through the specified node given by the gateway id """
        gateway_type = self.type(gateway)
        if gateway_type == VertexType.Z:
            pass # TODO
        elif gateway_type == VertexType.X:
            pass # TODO
        elif gateway_type == VertexType.H_BOX:
            pass # TODO (also what if this has multiple legs?
        else:
            raise NotImplementedError(f"Gateway type {gateway_type.name} unhandled right now")
