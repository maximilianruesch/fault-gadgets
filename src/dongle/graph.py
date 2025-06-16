from typing import Tuple, Dict, Iterable, Literal, List, Optional, Mapping

from pyzx.graph.base import upair
from pyzx.utils import toggle_edge
from .dongles import Dongle, DongleTarget, DongleTargetType
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

ET = Tuple[int, int]

class DongleGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._dongle_id_index = 0 # Counter which ID to assign to next dongle
        self._targets: Dict[int, DongleTarget] = dict() # target ID (node) -> target
        self._dongles: Dict[int, Dongle] = dict() # dongle ID -> dongle
        self._in_dongle: Dict[int, int] = dict() # target ID -> dongle ID
        self._on_edge: Dict[int, ET] = dict() # target ID -> edge the target is on
        self._targets_by_edge: Dict[ET, List[int]] = dict() # edge -> target ID

    def clone(self, instance: Optional['DongleGraph'] = None) -> 'DongleGraph':
        cpy = GraphS.clone(self, instance)
        cpy._dongle_id_index = self._dongle_id_index
        cpy._targets = self._targets.copy()
        cpy._dongles = { _id: dongle.copy() for _id, dongle in self._dongles.items() }
        cpy._in_dongle = self._in_dongle.copy()
        cpy._on_edge = self._on_edge.copy()
        cpy._targets_by_edge = { edge: targets.copy() for edge, targets in self._targets_by_edge.items() }

        return cpy

    @staticmethod
    def from_graph(graph: GraphS) -> 'DongleGraph':
        """
        Assumes that the given graph has no dongle information attached.
        If a graph with dongles needs to be copied, use `clone` instead.
        """
        return graph.clone(DongleGraph())

    def _local_info(self, _id: int) -> Tuple[int, int]:
        """
        Returns the actual graph left and right nodes, ignoring the distributor of the dongle the target is attached to

        :param _id: The target ID to fetch local info for
        :return: 'left' and 'right' adjacent nodes
        """
        dist = self._dongles[self._in_dongle[_id]].dist
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

    def dongles(self) -> Dict[int, Dongle]:
        return self._dongles

    def add_all_dongles(self) -> Mapping[ET, Tuple[int, int, int]]:
        if len(self._on_edge) != 0:
            raise ValueError(f"The graph already has some dongles!")

        edge_to_dongle_ids = dict()
        for e1, e2 in list(self.edges()):
            # Dongles on inputs and outputs do not change for rewrites, thus skip
            if self.type(e1) is VertexType.BOUNDARY or self.type(e2) is VertexType.BOUNDARY:
               continue

            edge_to_dongle_ids[(e1, e2)] = self.add_dongles((e1, e2))

        return edge_to_dongle_ids

    def add_dongles(self, edge: ET) -> Tuple[int, int, int]:
        edge_type = self.edge_type(edge)
        if edge_type == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not edge_type == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')

        return (self._add_dongle(types=['X'], edge=edge),
                self._add_dongle(types=['Z'], edge=edge),
                self._add_dongle(types=['Y'], edge=edge))

    def _add_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']], edge: Optional[ET] = None) -> int:
        spawn = self.add_vertex(VertexType.Z, qubit=-3)
        dist = self.add_vertex(VertexType.X, qubit=-2)
        self.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)

        _id = self._dongle_id_index
        dongle = Dongle(_id, spawn=spawn, dist=dist, targets=[])
        self._dongles[_id] = dongle
        self._dongle_id_index += 1

        for target_type in types:
            if target_type == 'X' or target_type == 'Y':
                self.add_target(DongleTargetType.X, dongle_id=_id, edge=edge)
            if target_type == 'Z' or target_type == 'Y':
                self.add_target(DongleTargetType.Z, dongle_id=_id, edge=edge)

        return _id

    def add_target(self, _type: DongleTargetType, dongle_id: int, edge: ET) -> DongleTarget:
        _id = self.add_vertex(VertexType.Z_BOX) # TODO choose a more appropriate node type
        _target = DongleTarget(id=_id, type=_type)
        self._targets[_id] = _target

        dongle = self._dongles[dongle_id]
        dongle.targets.append(_target)
        self._in_dongle[_id] = dongle_id
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
        _id = target.id

        left, right = self._local_info(_id)
        self.remove_vertex(_id)
        self.add_edge((left, right))
        self._update_target_edge(target, edge=None)

        dongle = self._dongles[self._in_dongle[_id]]
        dongle.targets.remove(target)
        del self._in_dongle[_id]
        if len(dongle.targets) == 0:
            self.remove_vertices([dongle.spawn, dongle.dist])
            del self._dongles[dongle.id]

        del self._targets[_id]

    def _remove_targets(self, targets: Iterable[DongleTarget]) -> None:
        for target in targets:
            self._remove_target(target)

    def _update_target_edge(self, target: DongleTarget, edge: Optional[ET]) -> None:
        _id = target.id
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
            self._on_edge[_id] = upair(*edge)

    def merge_targets(self, quiet: bool = True) -> None:
        for dongle_id in set(self._in_dongle.values()):
            self.merge_targets_of_dongle(dongle_id, quiet=quiet)

    def merge_targets_of_dongle(self, dongle_id: int, quiet: bool = True) -> None:
        x_targets_by_edge: Dict[ET, List[DongleTarget]] = dict()
        z_targets_by_edge: Dict[ET, List[DongleTarget]] = dict()
        for target in self._dongles[dongle_id].targets:
            edge = self._on_edge[target.id]
            if target.type == DongleTargetType.X:
                if not x_targets_by_edge.__contains__(edge):
                    x_targets_by_edge[edge] = []
                x_targets_by_edge[edge].append(target)
            else:
                if not z_targets_by_edge.__contains__(edge):
                    z_targets_by_edge[edge] = []
                z_targets_by_edge[edge].append(target)

        # All X targets from the same dongle on the same edge merge
        for edge, targets in x_targets_by_edge.items():
            if len(targets) % 2 == 1:
                targets.pop()
            if not quiet and len(targets) > 0:
                print(f"Reducing {len(targets)} targets of type X from dongle #{dongle_id} on edge {edge}!")
            self._remove_targets(targets)

        # All Z targets from the same dongle on the same edge merge
        for edge, targets in z_targets_by_edge.items():
            if len(targets) % 2 == 1:
                targets.pop()
            if not quiet and len(targets) > 0:
                print(f"Reducing {len(targets)} targets of type Z from dongle #{dongle_id} on edge {edge}!")
            self._remove_targets(targets)

    def reassign_dongle_positions(self):
        # Adjust all target positions
        for edge, target_ids in self._targets_by_edge.items():
            s,t = edge
            s_qubit, s_row = self.qubit(s), self.row(s)
            t_qubit, t_row = self.qubit(t), self.row(t)

            for idx, _id in enumerate(target_ids):
                self.set_qubit(_id, s_qubit + (t_qubit - s_qubit) * ((float(idx) + 1) / (len(target_ids) + 1)))
                self.set_row(_id, s_row + (t_row - s_row) * ((float(idx) + 1) / (len(target_ids) + 1)))

        # Adjust all distributors and spawn rows
        for dongle in self._dongles.values():
            rows = [self.row(target.id) for target in dongle.targets]
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
            if target.type == DongleTargetType.X:
                self.set_edge_type((left, _id), toggle_edge(self.edge_type((left, _id))))
                self.set_edge_type((_id, right), toggle_edge(self.edge_type((_id, right))))

    def full_instance(self) -> None:
        self.reassign_dongle_positions()
        self.realise_all_targets()
        self.pack_circuit_rows()
        self.auto_detect_io()
