from typing import Tuple, Dict, Iterable, Literal, List, Optional

from pyzx.graph.base import upair
from pyzx.utils import toggle_edge
from .dongles import Dongle, DongleTarget, DongleTargetType
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

ET = Tuple[int, int]

class ShieldedGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._target_id_index = 0 # Counter which ID to assign to next target
        self._targets: Dict[int, DongleTarget] = dict() # ID target ID -> Target
        self._in_dongle: Dict[int, Dongle] = dict() # target ID -> Dongle of target
        self._on_edge: Dict[int, ET] = dict() # target ID -> edge the target is on
        self._targets_by_edge: Dict[ET, List[int]] = dict() # edge -> target ID

    def clone(self, instance: Optional['ShieldedGraph'] = None) -> 'ShieldedGraph':
        cpy = GraphS.clone(self, instance)
        cpy._target_id_index = self._target_id_index
        cpy._targets = { _id: target.copy() for _id, target in self._targets.items() }
        cpy._in_dongle = { _id: dongle.copy() for _id, dongle in self._in_dongle.items() }
        cpy._on_edge = self._on_edge.copy()
        cpy._targets_by_edge = { edge: targets.copy() for edge, targets in self._targets_by_edge.items() }

        return cpy

    @staticmethod
    def from_graph(graph: GraphS) -> 'ShieldedGraph':
        """
        Assumes that the given graph has no dongle information attached.
        If a graph with dongles needs to be copied, use `clone` instead.
        """
        return graph.clone(ShieldedGraph())

    def _local_info(self, _id: int) -> Tuple[int, int]:
        """
        Returns the actual graph left and right nodes, ignoring the distributor of the dongle the target is attached to

        :param _id: The target ID to fetch local info for
        :return: 'left' and 'right' adjacent nodes
        """
        dist = self._in_dongle[_id].dist
        adjacent_nodes = [
            e1 if e2 == _id else e2
            for e1, e2, in self.edges(_id)
        ]
        if len(adjacent_nodes) != 3:
            raise ValueError(f"The given target {_id} is not adjacent to exactly 3 other nodes!")
        elif not adjacent_nodes.__contains__(dist):
            raise RuntimeError(f"The given target {_id} is not adjacent to its distributor!")
        adjacent_nodes.remove(dist)
        return adjacent_nodes[0], adjacent_nodes[1]

    ###########################################################
    #                        Dongles                          #
    ###########################################################

    def dongles(self):
        return set(self._in_dongle.values())

    def add_all_dongles(self):
        if len(self._on_edge) != 0:
            raise ValueError(f"The graph already has some dongles!")

        for edge in list(self.edges()):
            self.add_dongles(edge)

    def add_dongles(self, edge: ET) -> Tuple[Dongle, Dongle, Dongle]:
        edge_type = self.edge_type(edge)
        if edge_type == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not edge_type == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')

        return (self._add_dongle(types=['X'], edge=edge),
                self._add_dongle(types=['Z'], edge=edge),
                self._add_dongle(types=['Y'], edge=edge))

    def _add_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']], edge: Optional[ET] = None) -> Dongle:
        spawn = self.add_vertex(VertexType.Z, qubit=-3)
        dist = self.add_vertex(VertexType.X, qubit=-2)
        self.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)
        dongle = Dongle(self, spawn=spawn, dist=dist, targets=[])

        for target_type in types:
            if target_type == 'X' or target_type == 'Y':
                self.add_target(DongleTargetType.X, dongle=dongle, edge=edge)
            if target_type == 'Z' or target_type == 'Y':
                self.add_target(DongleTargetType.Z, dongle=dongle, edge=edge)

        return dongle

    def add_target(self, _type: DongleTargetType, dongle: Dongle, edge: ET) -> DongleTarget:
        _id = self.add_vertex(VertexType.Z_BOX) # TODO choose a more appropriate node type
        _target = DongleTarget(_id=_id, _type=_type)
        self._targets[_id] = _target

        dongle.targets.append(_target)
        self._in_dongle[_id] = dongle
        self.add_edge((dongle.dist, _id))

        # Connect with neighbouring targets
        other_targets_on_edge = self._targets_by_edge.get(upair(*edge)) or []
        if len(other_targets_on_edge) == 0:
            self.remove_edge(edge)
            self.add_edges([(edge[0], _id), (_id, edge[1])])
        else:
            other_id = other_targets_on_edge[-1]
            _, right = self._local_info(other_id)
            self.remove_edge((other_id, right))
            self.add_edges([(other_id, _id), (_id, right)])
        self._update_target_edge(target=_target, edge=edge)

        return _target

    def _remove_target(self, target: DongleTarget) -> None:
        _id = target.get_id()
        dongle = self._in_dongle[_id]
        dongle.targets.remove(target)

        left, right = self._local_info(_id)
        self.remove_vertex(_id)
        self.add_edge((left, right))

        del self._targets[_id]
        del self._in_dongle[_id]
        self._update_target_edge(target, edge=None)

    def _remove_targets(self, targets: Iterable[DongleTarget]) -> None:
        for target in targets:
            self._remove_target(target)

    def _update_target_edge(self, target: DongleTarget, edge: Optional[ET]) -> None:
        _id = target.get_id()
        old_edge = self._on_edge.get(_id)
        if old_edge is None and edge is None:
            return

        if edge is None:
            self._targets_by_edge[upair(*old_edge)].remove(_id)
            del self._on_edge[_id]
        else:
            if old_edge is not None:
                old_edge = self._on_edge[_id]
                self._targets_by_edge[upair(*old_edge)].remove(_id)
            if not self._targets_by_edge.__contains__(upair(*edge)):
                self._targets_by_edge[upair(*edge)] = []
            self._targets_by_edge[upair(*edge)].append(_id)
            self._on_edge[_id] = edge

    def merge_targets(self) -> None:
        for dongle in set(self._in_dongle.values()):
            self.merge_targets_of_dongle(dongle)

    def merge_targets_of_dongle(self, dongle: Dongle) -> None:
        x_targets_by_edge: Dict[ET, List[DongleTarget]] = dict()
        z_targets_by_edge: Dict[ET, List[DongleTarget]] = dict()
        for target in dongle.targets:
            edge = self._on_edge[target.get_id()]
            if target.get_type() == DongleTargetType.X:
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

    def reassign_dongle_positions(self):
        # Adjust all target positions
        for edge, targets in self._targets_by_edge.items():
            s,t = edge
            s_qubit, s_row = self.qubit(s), self.row(s)
            t_qubit, t_row = self.qubit(t), self.row(t)

            if s_qubit == t_qubit:  # Horizontal
                for idx, _id in enumerate(targets):
                    self.set_qubit(_id, s_qubit)
                    self.set_row(_id,
                                 s_row + (t_row - s_row) * ((float(idx) + 1) / (len(targets) + 1)))
            elif s_row == t_row:  # Vertical
                for idx, _id in enumerate(targets):
                    self.set_qubit(_id,
                                   s_qubit + (t_qubit - s_qubit) * ((float(idx) + 1) / (len(targets) + 1)))
                    self.set_row(_id, s_row)
            else:
                raise ValueError("Underlying diagram is not on a grid!")

        # Adjust all distributors and spawn rows
        for dongle in self._in_dongle.values():
            rows = [self.row(target.get_id()) for target in dongle.targets]
            avg_row = sum(rows) / len(dongle.targets)
            self.set_row(dongle.dist, avg_row)
            self.set_row(dongle.spawn, avg_row)

    ###########################################################
    #                       Realising                         #
    ###########################################################

    def realise_all_targets(self) -> None:
        for _id, target in self._targets.items():
            self.set_type(_id, VertexType.Z)
            left, right = self._local_info(_id)
            if target.get_type() == DongleTargetType.X:
                self.set_edge_type((left, _id), toggle_edge(self.edge_type((left, _id))))
                self.set_edge_type((_id, right), toggle_edge(self.edge_type((_id, right))))

    def full_instance(self) -> None:
        self.reassign_dongle_positions()
        self.realise_all_targets()
        self.pack_circuit_rows()
        self.auto_detect_io()

    ###########################################################
    #                       Pushing                           #
    ###########################################################

    def push_target(self, target: DongleTarget, new_edge: ET) -> Iterable[DongleTarget]:
        """
        Push the target to the next edge which must be adjacent.
        May have side effects on the target / introduce new targets / remove target.
        """
        if self.edge_type(new_edge) == EdgeType.HADAMARD:
            raise ValueError("Hadamard edges cannot be pushed onto!")

        _id = target.get_id()
        old_edge = self._on_edge[_id]
        common_nodes = set(old_edge).intersection(new_edge)
        if len(common_nodes) == 2:
            raise ValueError(f"Given target is already on the edge: {new_edge}!")
        elif len(common_nodes) == 0:
            raise ValueError(f"Given edge {new_edge} is not adjacent to dongle target edge {old_edge}!")

        gateway = common_nodes.pop()
        co_gateway = set(old_edge).difference(common_nodes).pop()
        gateway_type = self.type(gateway)

        def _teleport() -> Tuple[int, int]:
            left, right = self._local_info(_id)
            other_target = None
            for e1, e2 in self.edges(gateway):
                if e1 == gateway and self._on_edge.__contains__(e2) and self._on_edge[e2] == old_edge:
                    other_target = e2
                elif e2 == gateway and self._on_edge.__contains__(e1) and self._on_edge[e1] == old_edge:
                    other_target = e1

            if other_target is None:
                raise RuntimeError(f"Cannot find next target on edge {old_edge} where one is supposed to be!")
            elif other_target == _id:
                # Nothing to do, already adjacent to gateway!
                return (left, right) if left == gateway else (right, left)

            self.remove_edges([(gateway, other_target), (left, _id), (right, _id)])
            self.add_edges([(left, right), (gateway, _id), (other_target, _id)])

            return gateway, other_target

        def _phase_through() -> None:
            _s, _t = _teleport()
            self.remove_edges([new_edge, (_s, _id), (_t, _id)])
            self.add_edges([(_s, _t), (new_edge[1], _id), (new_edge[0], _id)])
            self._update_target_edge(target, new_edge)

        def _multiply_through(_type: DongleTargetType) -> Iterable[DongleTarget]:
            _s, _t = _teleport()
            dongle = self._in_dongle[_id]
            new_targets = []
            for e1, e2 in list(self.edges(gateway)):
                other = e1 if gateway == e2 else e2
                if other != co_gateway: # Skip the edge that the target is pushed from
                    new_targets.append(self.add_target(_type, dongle=dongle, edge=(e1, e2)))
            self._remove_target(target)
            return new_targets

        if gateway_type == VertexType.Z:
            if target.get_type() == DongleTargetType.Z:
                _phase_through()
                return [target]
            else:
                return _multiply_through(DongleTargetType.X)
        elif gateway_type == VertexType.X:
            if target.get_type() == DongleTargetType.X:
                _phase_through()
                return [target]
            else:
                return _multiply_through(DongleTargetType.Z)
        elif gateway_type == VertexType.H_BOX:
            _phase_through()
            target.set_type(target.get_type().flip())
            return [target]
        else:
            raise NotImplementedError(f"Gateway type {gateway_type.name} unhandled right now!")
