from typing import Tuple, Dict, Iterable, Literal, List, Optional, Mapping, NamedTuple

from pyzx.graph.base import upair
from .dongles import Dongle, DongleTarget, DongleTargetType
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

ET = Tuple[int, int]

class Nodes:
    class DongleNodes(NamedTuple):
        spawn: int
        dist: int

    dongles: Dict[int, DongleNodes] # dongle ID -> (spawn node, dist node)
    targets: Dict[int, List[int]] # dongle ID -> target node
    targets_by_edge: Dict[ET, List[int]] # edge -> target node

    def __init__(self):
        self.dongles = dict()
        self.targets = dict()
        self.targets_by_edge = dict()

class DongleGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._dongle_id_index = 0 # Counter which ID to assign to next dongle
        self._dongles: Dict[int, Dongle] = dict() # dongle ID -> dongle

        self._target_id_index = 0 # Counter which ID to assign to next target
        self._targets: Dict[int, DongleTarget] = dict() # target ID -> target
        self._in_dongle: Dict[int, int] = dict() # target ID -> dongle ID
        self._on_edge: Dict[int, ET] = dict() # target ID -> edge the target is on
        self._targets_by_edge: Dict[ET, List[int]] = dict() # edge -> target ID

    def clone(self, instance: Optional['DongleGraph'] = None) -> 'DongleGraph':
        cpy = GraphS.clone(self, instance)
        cpy._dongle_id_index = self._dongle_id_index
        cpy._dongles = { _id: dongle.copy() for _id, dongle in self._dongles.items() }

        cpy._target_id_index = self._target_id_index
        cpy._targets = self._targets.copy()
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

    ###########################################################
    #                        Dongles                          #
    ###########################################################

    def dongles(self) -> Dict[int, Dongle]:
        return self._dongles

    def add_all_dongles(self) -> Mapping[ET, Tuple[int, int, int]]:
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

        return (self.add_dongle(types=['X'], edge=edge),
                self.add_dongle(types=['Z'], edge=edge),
                self.add_dongle(types=['Y'], edge=edge))

    def add_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']], edge: ET) -> int:
        _id = self._dongle_id_index
        dongle = Dongle(_id, targets=[])
        self._dongles[_id] = dongle
        self._dongle_id_index += 1

        for target_type in types:
            if target_type == 'X' or target_type == 'Y':
                self.add_target(DongleTargetType.X, dongle_id=_id, edge=edge)
            if target_type == 'Z' or target_type == 'Y':
                self.add_target(DongleTargetType.Z, dongle_id=_id, edge=edge)

        return _id

    def add_target(self, _type: DongleTargetType, dongle_id: int, edge: ET) -> DongleTarget:
        if self.edge_type(edge) == 0:
            raise ValueError(f"Cannot add a target to a nonexistent edge: {edge}!")

        _id = self._target_id_index
        _target = DongleTarget(id=_id, type=_type)
        self._targets[_id] = _target
        self._target_id_index += 1

        dongle = self._dongles[dongle_id]
        dongle.targets.append(_target)
        self._in_dongle[_id] = dongle_id

        self._update_target_edge(target=_target, edge=edge)

        return _target

    def _remove_targets(self, targets: Iterable[DongleTarget]) -> None:
        for target in targets:
            self._remove_target(target)

    def _remove_target(self, target: DongleTarget) -> None:
        _id = target.id
        self._update_target_edge(target, edge=None)

        dongle = self._dongles[self._in_dongle[_id]]
        dongle.targets.remove(target)
        del self._in_dongle[_id]
        if len(dongle.targets) == 0:
            del self._dongles[dongle.id]
        del self._targets[_id]

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

    ###########################################################
    #                       Realising                         #
    ###########################################################

    def realise(self) -> Tuple[GraphS, Nodes]:
        graph = GraphS.clone(self)
        nodes = Nodes()
        target_nodes = dict()

        # Instance dongles
        for dongle_id, dongle in self._dongles.items():
            spawn, dist = graph.add_vertex(VertexType.Z, qubit=-3), graph.add_vertex(VertexType.X, qubit=-2)
            nodes.dongles[dongle_id] = Nodes.DongleNodes(spawn, dist)
            graph.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)

            for target in dongle.targets:
                _target_node = graph.add_vertex(VertexType.Z)
                target_nodes[target.id] = _target_node
                graph.add_edge((dist, _target_node))

        # Instance targets
        for edge, target_ids in self._targets_by_edge.items():
            left, right = edge
            s_qubit, s_row = graph.qubit(left), graph.row(left)
            t_qubit, t_row = graph.qubit(right), graph.row(right)

            nodes.targets_by_edge[edge] = [target_nodes[target_id] for target_id in target_ids]

            etab = dict()
            last_was_x_target = False
            for idx, target_id in enumerate(target_ids):
                target = self._targets[target_id]
                target_node = target_nodes[target_id]

                # Position target
                graph.set_qubit(target_node, s_qubit + (t_qubit - s_qubit) * ((float(idx) + 1) / (len(target_ids) + 1)))
                graph.set_row(target_node, s_row + (t_row - s_row) * ((float(idx) + 1) / (len(target_ids) + 1)))

                # Connect to neighbours
                h_edge = (target.type == DongleTargetType.X) ^ last_was_x_target
                last_was_x_target = target.type == DongleTargetType.X
                etab[(left, target_node)] = (not h_edge, h_edge)
                left = target_node

                # Register neighbours with target node information
                dongle_id = self._in_dongle[target_id]
                if dongle_id not in nodes.targets: nodes.targets[dongle_id] = []
                nodes.targets[dongle_id].append(target_node)

            etab[(left, right)] = (not last_was_x_target, last_was_x_target)

            graph.remove_edge(edge)
            graph.add_edge_table(etab)

        # Adjust dongle positions
        for dongle in self._dongles.values():
            rows = [graph.row(target.id) for target in dongle.targets]
            avg_row = sum(rows) / len(dongle.targets)
            graph.set_row(nodes.dongles[dongle.id].dist, avg_row)
            graph.set_row(nodes.dongles[dongle.id].spawn, avg_row)

        return graph, nodes
