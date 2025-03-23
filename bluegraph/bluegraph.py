from typing import Tuple, Dict, Iterable, Literal, List

from .dongles import Dongle, DongleTarget, DongleTargetType
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

class BlueGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._blue: Dict[Tuple[int, int], bool] = dict()
        self._targets: Dict[int, DongleTarget] = dict() # ID (main node) -> Target
        self._in_dongle: Dict[int, Dongle] = dict() # ID (main node) -> Dongle of target
        self._on_edge: Dict[int, Tuple[int, int]] = dict() # ID (main node) -> 'real' edge the target is on
        self._distributors: Dict[int, int] = dict() # ID (main node) -> Distributor
        self._realized: Dict[int, bool] = dict() # ID (main node) -> 'realized' as bool value

    def clone(self):
        cpy = GraphS.clone(self)
        cpy._blue = self._blue.copy()
        cpy._targets = self._targets.copy()
        cpy._in_dongle = self._in_dongle.copy()
        cpy._on_edge = self._on_edge.copy()
        cpy._distributors = self._distributors.copy()
        cpy._realized = self._realized.copy()

        return cpy

    def _add_blue_edges(self, edges: Iterable[Tuple[int, int]]) -> None:
        self.add_edges(edges, edgetype=EdgeType.SIMPLE)
        for (s,t) in edges:
            self._blue[(s,t)] = True
            self._blue[(t,s)] = True

    def _is_blue(self, edge: Tuple[int, int]) -> bool:
        return self._blue[edge]

    def _set_on_edge(self, target_ids: Iterable[int], edge: Tuple[int, int]) -> None:
        for target_id in target_ids:
            self._on_edge[target_id] = edge

    def _local_target_info(self, id_node: int) -> Tuple[int, int, int]:
        """
        :param id_node: The id of the target to fetch local info for
        :return: The next distributor + 'left' and 'right' adjacent nodes
        """
        dist = self._distributors[id_node]
        adjacent_nodes = [
            e1 if e2 == id_node else e2
            for e1, e2, in self.edges(id_node)
        ]
        if len(adjacent_nodes) != 3:
            raise ValueError(f"The given node {id_node} is not adjacent to exactly 3 other nodes!")
        elif not adjacent_nodes.__contains__(dist):
            raise RuntimeError(f"The given node {id_node} is not adjacent to its distributor!")
        adjacent_nodes.remove(dist)
        return dist, adjacent_nodes[0], adjacent_nodes[1]

    def remove_edge(self, edge):
        GraphS.remove_edge(self, edge)
        if self._blue.__contains__(edge):
            del self._blue[edge]

    def remove_edges(self, edges):
        GraphS.remove_edges(self, edges)
        for edge in edges:
            if self._blue.__contains__(edge):
                del self._blue[edge]

    def add_dongles(self, edge: Tuple[int, int], repack=False) -> Tuple[Dongle, Dongle, Dongle]:
        edge_type = self.edge_type(edge)
        if edge_type == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not edge_type == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')

        self.remove_edge(edge)

        s,t = edge

        z_dongle, z_target = self._z_dongle()
        x_dongle, x_target = self._x_dongle()
        y_dongle, y_target_1, y_target_2 = self._y_dongle()

        self._add_blue_edges([
            (s, z_target),
            (z_target, x_target),
            (x_target, y_target_1),
            (y_target_1, y_target_2),
            (y_target_2, t),
        ])
        self._set_on_edge([z_target, x_target, y_target_1, y_target_2], edge)

        if repack:
            self.pack_circuit_rows()

        assert self.is_well_formed(), "Circuit is not well formed anymore!"

        return x_dongle, z_dongle, y_dongle

    def _x_dongle(self) -> Tuple[Dongle, int]:
        dongle = self._instantiate_dongle(types=['X'])
        return dongle, dongle.targets[0].get_id()

    def _z_dongle(self) -> Tuple[Dongle, int]:
        dongle = self._instantiate_dongle(types=['Z'])
        return dongle, dongle.targets[0].get_id()

    def _y_dongle(self) -> Tuple[Dongle, int, int]:
        dongle = self._instantiate_dongle(types=['Y'])
        return dongle, dongle.targets[0].get_id(), dongle.targets[1].get_id()

    def _instantiate_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']]):
        spawn = self.add_vertex(VertexType.Z, qubit=-4, row=1.2)
        dist = self.add_vertex(VertexType.X, qubit=-3, row=1.2)

        self.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)
        blue_edges = [(spawn, dist)]
        targets = []

        for target_type in types:
            if target_type == 'X':
                targets.append(self._add_target(DongleTargetType.X, dist))
            elif target_type == 'Z':
                targets.append(self._add_target(DongleTargetType.Z, dist))
            else:
                local_dist = self.add_vertex(VertexType.X, qubit=-2, row=1.5)
                targets.append(self._add_target(DongleTargetType.X, local_dist))
                targets.append(self._add_target(DongleTargetType.Z, local_dist))
                blue_edges.append((dist, local_dist))

        self._add_blue_edges(blue_edges)
        dongle = Dongle(self, spawn, dist, targets)
        for target in targets:
            self._in_dongle[target.get_id()] = dongle

        return dongle

    def _add_target(self, _type: DongleTargetType, local_distributor: int):
        # TODO choose a more appropriate node type
        _id_node = self.add_vertex(VertexType.Z_BOX, qubit=-1, row=1.7)
        _target = DongleTarget(
            _id=_id_node,
            target_type=_type
        )
        self._targets[_id_node] = _target
        self._distributors[_id_node] = local_distributor
        self._realized[_id_node] = False
        self._add_blue_edges([(local_distributor, _id_node)])

        return _target

    def _remove_target(self, target: DongleTarget) -> None:
        _id_node = target.get_id()
        if self._realized[_id_node]:
            raise ValueError("Target is already realized, cannot remove!")

        dongle = self._in_dongle[_id_node]
        dongle.targets.remove(target)

        _, s, t = self._local_target_info(_id_node)
        self._add_blue_edges([(s, t)])

        self.remove_vertex(_id_node)
        del self._targets[_id_node]
        del self._in_dongle[_id_node]
        del self._on_edge[_id_node]
        del self._distributors[_id_node]
        del self._realized[_id_node]

    def _remove_targets(self, targets: Iterable[DongleTarget]) -> None:
        for target in targets:
            self._remove_target(target)

    def realise_all_targets(self) -> None:
        for id_node, target in self._targets.items():
            ntype = target.get_target_type()
            dist, adj_left, adj_right = self._local_target_info(id_node)

            new_edges = []
            if ntype == DongleTargetType.X:
                hadamard_left = self.add_vertex(VertexType.H_BOX, qubit=-1, row=1.7)
                new_node = self.add_vertex(VertexType.Z, qubit=-1, row=1.8)
                hadamard_right = self.add_vertex(VertexType.H_BOX, qubit=-1, row=1.9)
                new_edges.extend([
                    (dist, new_node),
                    (hadamard_left, new_node),
                    (new_node, hadamard_right),
                    (adj_left, hadamard_left),
                    (adj_right, hadamard_right),
                ])
            elif ntype == DongleTargetType.Z:
                new_node = self.add_vertex(VertexType.Z, qubit=-1, row=1.6)
                new_edges.extend([
                    (dist, new_node),
                    (adj_left, new_node),
                    (adj_right, new_node),
                ])
            else:
                raise RuntimeError(f"Unexpected blue target type: {ntype}")
            self.remove_vertex(id_node)
            self._add_blue_edges(new_edges)
            self._realized[id_node] = True

    def push_target(self, target: DongleTarget, new_edge: Tuple[int, int]) -> None:
        """
        Push the target to the next edge which must be adjacent.
        May have side effects on the target / introduce new targets / remove target.
        """
        id_node = target.get_id()
        if self._realized[id_node]: raise ValueError("Target already realized, cannot push!")
        dist, s, t = self._local_target_info(id_node)

        old_edge = self._on_edge[id_node]
        common_nodes = set(old_edge).intersection(new_edge)
        if len(common_nodes) == 2:
            raise ValueError(f"Given target is already on the edge: {new_edge}!")
        elif len(common_nodes) == 0:
            raise ValueError(f"Given edge {new_edge} is not adjacent to dongle target edge {old_edge}!")

        gateway = common_nodes.pop()
        gateway_type = self.type(gateway)

        def _teleport() -> Tuple[int, int]:
            """
            Phase through other dongle targets to be adjacent to the gateway
            :return: new adjacent nodes to the id_node
            """
            other_target = None
            for e1, e2 in self.edges(gateway):
                if e1 == gateway and self._on_edge.__contains__(e2) and self._on_edge[e2] == old_edge:
                    other_target = e2
                elif e2 == gateway and self._on_edge.__contains__(e1) and self._on_edge[e1] == old_edge:
                    other_target = e1

            if other_target is None:
                raise RuntimeError(f"Cannot find next target on edge {old_edge} where one is supposed to be!")
            elif other_target == id_node:
                # Nothing to do, already at the desired edge!
                return (s, t) if s == gateway else (t, s)

            self.remove_edges([(gateway, other_target), (s, id_node), (t, id_node)])
            self._add_blue_edges([(s, t), (gateway, id_node), (other_target, id_node)])

            return gateway, other_target

        def _phase_through() -> None:
            _s, _t = _teleport()
            self.remove_edges([new_edge, (_s, id_node), (_t, id_node)])
            self._add_blue_edges([(_s, _t), (new_edge[1], id_node), (new_edge[0], id_node)])
            self._on_edge[id_node] = new_edge

        def _multiply_through(_type: DongleTargetType):
            _s, _t = _teleport()
            dongle = self._in_dongle[id_node]
            for e1, e2 in list(self.edges(gateway)):
                other = e1 if gateway == e2 else e2
                if other != id_node:
                    self.remove_edge((e1, e2))
                    new_target = self._add_target(_type, dist)
                    dongle.targets.append(new_target)
                    self._add_blue_edges([(e1, new_target.get_id()), (e2, new_target.get_id())])
                    self._in_dongle[new_target.get_id()] = dongle
                    if self._on_edge.__contains__(other):
                        # If the adjacent node is a target, assume that its _on_edge is correctly set, so just copy
                        self._on_edge[new_target.get_id()] = self._on_edge[other]
                    else:
                        self._on_edge[new_target.get_id()] = (e1, e2)

            self._remove_target(target)

        if gateway_type == VertexType.Z:
            if target.get_target_type() == DongleTargetType.Z:
                _phase_through()
            else:
                _multiply_through(DongleTargetType.X)
        elif gateway_type == VertexType.X:
            if target.get_target_type() == DongleTargetType.X:
                _phase_through()
            else:
                _multiply_through(DongleTargetType.Z)
        elif gateway_type == VertexType.H_BOX:
            # Can just teleport through by converting to other target type
            _phase_through()
            target.set_target_type(
                DongleTargetType.Z if target.get_target_type() == DongleTargetType.X else DongleTargetType.X
            )
        else:
            raise NotImplementedError(f"Gateway type {gateway_type.name} unhandled right now!")

    def merge_all_targets(self) -> None:
        for dongle in set(self._in_dongle.values()):
            x_targets_by_edge: Dict[Tuple[int, int], List[DongleTarget]] = dict()
            z_targets_by_edge: Dict[Tuple[int, int], List[DongleTarget]] = dict()
            for target in dongle.targets:
                edge = self._on_edge[target.get_id()]
                if target.get_target_type() == DongleTargetType.X:
                    if not x_targets_by_edge.__contains__(edge):
                        x_targets_by_edge[edge] = []
                    x_targets_by_edge[edge].append(target)
                else:
                    if not z_targets_by_edge.__contains__(edge):
                        z_targets_by_edge[edge] = []
                    z_targets_by_edge[edge].append(target)

            # All X targets from the same dongle on the same edge merge
            for targets in x_targets_by_edge.values():
                if len(targets) % 2 == 1:
                    targets.pop()
                self._remove_targets(targets)

            # All Z targets from the same dongle on the same edge merge
            for targets in z_targets_by_edge.values():
                if len(targets) % 2 == 1:
                    targets.pop()
                self._remove_targets(targets)

