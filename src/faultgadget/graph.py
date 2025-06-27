import math
from typing import Tuple, Dict, Iterable, Literal, List, Optional, NamedTuple

from pyzx.graph.base import upair
from .gadget import Gadget, Target, TargetType
from .sink import Sink, SinkType
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

ET = Tuple[int, int]

class Nodes:
    class GadgetNodes(NamedTuple):
        spawn: int
        dist: int

    class SinkNodes(NamedTuple):
        gate: int
        end: int

    gadgets: Dict[int, GadgetNodes] # gadget ID -> (spawn node, dist node)
    targets: Dict[int, List[int]] # gadget ID -> target node
    extra_nodes_by_edge: Dict[ET, List[int]] # edge -> extra nodes like targets and sinks
    sinks: Dict[int, SinkNodes] # sink ID -> (gate node, end node)
    sinks_by_edge: Dict[ET, int] # edge -> gate node

    def __init__(self):
        self.gadgets = dict()
        self.targets = dict()
        self.extra_nodes_by_edge = dict()
        self.sinks = dict()
        self.sinks_by_edge = dict()

class GadgetGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._gadget_id_index = 0 # Counter which ID to assign to next gadget
        self._gadgets: Dict[int, Gadget] = dict() # gadget ID -> gadget

        self._target_id_index = 0 # Counter which ID to assign to next target
        self._targets: Dict[int, Target] = dict() # target ID -> target
        self._in_gadget: Dict[int, int] = dict() # target ID -> gadget ID
        self._on_edge: Dict[int, ET] = dict() # target ID -> edge the target is on
        self._targets_by_edge: Dict[ET, List[int]] = dict() # edge -> target ID

        self._sink_id_index = 0 # Counter which ID to assign to next sink
        self._sinks: Dict[int, Sink] = dict() # sink ID -> sink
        self._sink_on_edge: Dict[int, ET] = dict() # sink ID -> edge the sink is on
        self._sinks_by_edge: Dict[ET, int] = dict() # edge -> sink ID
        self._in_sink: Dict[int, int] = dict() # target ID -> sink ID

    def clone(self, instance: Optional['GadgetGraph'] = None) -> 'GadgetGraph':
        cpy = GraphS.clone(self, instance)
        cpy._gadget_id_index = self._gadget_id_index
        cpy._gadgets = {_id: gadget.copy() for _id, gadget in self._gadgets.items()}

        cpy._target_id_index = self._target_id_index
        cpy._targets = self._targets.copy()
        cpy._in_gadget = self._in_gadget.copy()
        cpy._on_edge = self._on_edge.copy()
        cpy._targets_by_edge = { edge: targets.copy() for edge, targets in self._targets_by_edge.items() }

        cpy._sink_id_index = self._sink_id_index
        cpy._sinks = self._sinks.copy()
        cpy._sink_on_edge = self._sink_on_edge.copy()
        cpy._sinks_by_edge = self._sinks_by_edge.copy()
        cpy._in_sink = self._in_sink.copy()

        return cpy

    @staticmethod
    def from_graph(graph: GraphS) -> 'GadgetGraph':
        """
        Assumes that the given graph has no gadget information attached.
        If a graph with gadgets needs to be copied, use `clone` instead.
        """
        return graph.clone(GadgetGraph())

    ###########################################################
    #                        Gadgets                          #
    ###########################################################

    def gadgets(self) -> Dict[int, Gadget]:
        return self._gadgets

    def add_edge_flip_gadgets(self, edge: ET) -> Tuple[int, int, int]:
        return (self.add_gadget(types=['X'], edge=edge),
                self.add_gadget(types=['Z'], edge=edge),
                self.add_gadget(types=['Y'], edge=edge))

    def add_gadget(self, types: Iterable[Literal['X', 'Y', 'Z']], edge: ET) -> int:
        if self.edge_type(edge) == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not self.edge_type(edge) == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')

        _id = self._gadget_id_index
        self._gadgets[_id] = Gadget(_id, targets=[])
        self._gadget_id_index += 1

        for target_type in types:
            if target_type == 'X' or target_type == 'Y':
                self.add_target_on_edge(TargetType.X, gadget_id=_id, edge=edge)
            if target_type == 'Z' or target_type == 'Y':
                self.add_target_on_edge(TargetType.Z, gadget_id=_id, edge=edge)

        return _id

    def add_target_on_edge(self, _type: TargetType, gadget_id: int, edge: ET) -> Target:
        if self.edge_type(edge) == 0:
            raise ValueError(f"Cannot add a target to a nonexistent edge: {edge}!")

        _target = self._add_target(_type=_type, gadget_id=gadget_id)
        self._update_target_edge(_target.id, edge=edge)

        return _target

    def _add_target(self, _type: TargetType, gadget_id: int) -> Target:
        _id = self._target_id_index
        _target = Target(id=_id, type=_type)
        self._targets[_id] = _target
        self._target_id_index += 1

        gadget = self._gadgets[gadget_id]
        gadget.targets.append(_target)
        self._in_gadget[_id] = gadget_id

        return _target

    def _remove_targets(self, targets: Iterable[Target]) -> None:
        for target in targets:
            self._remove_target(target)

    def _remove_target(self, target: Target) -> None:
        _id = target.id
        self._update_target_edge(target.id, edge=None)

        gadget = self._gadgets[self._in_gadget[_id]]
        gadget.targets.remove(target)
        del self._in_gadget[_id]
        if len(gadget.targets) == 0:
            del self._gadgets[gadget.id]
        del self._targets[_id]

    def _update_target_edge(self, target_id: int, edge: Optional[ET]) -> None:
        old_edge = self._on_edge.get(target_id)
        if old_edge is None and edge is None:
            return

        if edge is None:
            self._targets_by_edge[upair(*old_edge)].remove(target_id)
            del self._on_edge[target_id]
        else:
            if old_edge is not None:
                old_edge = self._on_edge[target_id]
                self._targets_by_edge[upair(*old_edge)].remove(target_id)
            if not self._targets_by_edge.__contains__(upair(*edge)):
                self._targets_by_edge[upair(*edge)] = []
            self._targets_by_edge[upair(*edge)].append(target_id)
            self._on_edge[target_id] = upair(*edge)

    def merge_targets(self, quiet: bool = True) -> None:
        for gadget_id in set(self._in_gadget.values()):
            self.merge_targets_of_gadget(gadget_id, quiet=quiet)

    def merge_targets_of_gadget(self, gadget_id: int, quiet: bool = True) -> None:
        x_targets_by_edge: Dict[ET, List[Target]] = dict()
        z_targets_by_edge: Dict[ET, List[Target]] = dict()
        targets_by_sink: Dict[int, List[Target]] = dict()
        for target in self._gadgets[gadget_id].targets:
            if target.id in self._on_edge:
                edge = self._on_edge[target.id]
                if target.type == TargetType.X:
                    if edge not in x_targets_by_edge: x_targets_by_edge[edge] = []
                    x_targets_by_edge[edge].append(target)
                else:
                    if edge not in z_targets_by_edge: z_targets_by_edge[edge] = []
                    z_targets_by_edge[edge].append(target)
            elif target.id in self._in_sink:
                sink_id = self._in_sink[target.id]
                if sink_id not in targets_by_sink: targets_by_sink[sink_id] = []
                targets_by_sink[sink_id].append(target)
            else:
                raise RuntimeError(f"Target {target.id} is at unknown location!")

        # All X targets from the same gadget on the same edge merge
        for edge, targets in x_targets_by_edge.items():
            if len(targets) % 2 == 1:
                targets.pop()
            if not quiet and len(targets) > 0:
                print(f"Reducing {len(targets)} targets of type X from gadget #{gadget_id} on edge {edge}!")
            self._remove_targets(targets)

        # All Z targets from the same gadget on the same edge merge
        for edge, targets in z_targets_by_edge.items():
            if len(targets) % 2 == 1:
                targets.pop()
            if not quiet and len(targets) > 0:
                print(f"Reducing {len(targets)} targets of type Z from gadget #{gadget_id} on edge {edge}!")
            self._remove_targets(targets)

    ###########################################################
    #                        Sinks                            #
    ###########################################################

    def sinks(self) -> Dict[int, Sink]:
        return self._sinks

    def add_sink(self, edge: ET, ty: SinkType) -> Sink:
        _id = self._sink_id_index
        sink = Sink(_id, ty)
        self._sinks[_id] = sink
        self._sink_id_index += 1

        self._sink_on_edge[_id] = upair(*edge)
        self._sinks_by_edge[upair(*edge)] = _id

        return sink

    def add_target_in_sink(self, _type: TargetType, gadget_id: int, sink_id: int):
        if sink_id not in self._sinks:
            raise ValueError(f"Cannot add a target to a nonexistent sink: {sink_id}!")

        _target = self._add_target(_type=_type, gadget_id=gadget_id)
        self._in_sink[_target.id] = sink_id

        return _target

    ###########################################################
    #                       Realising                         #
    ###########################################################

    def realise(self) -> Tuple[GraphS, Nodes]:
        graph = GraphS.clone(self)
        nodes = Nodes()
        target_nodes = dict()

        # Instance gadgets and their targets
        for gadget_id, gadget in self._gadgets.items():
            spawn, dist = graph.add_vertex(VertexType.Z, qubit=-3), graph.add_vertex(VertexType.X, qubit=-2)
            nodes.gadgets[gadget_id] = Nodes.GadgetNodes(spawn, dist)
            graph.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)

            for target in gadget.targets:
                _target_node = graph.add_vertex(VertexType.Z)
                target_nodes[target.id] = _target_node
                graph.add_edge((dist, _target_node))

        # Instance sinks
        for sink_id, sink in self._sinks.items():
            _ty = VertexType.X if sink.type is SinkType.X else VertexType.Z
            gate, end = graph.add_vertex(ty=_ty), graph.add_vertex(ty=_ty)
            nodes.sinks[sink_id] = Nodes.SinkNodes(gate, end)
            graph.add_edge((gate, end), edgetype=EdgeType.SIMPLE)

        edges = self._targets_by_edge.keys() | self._sinks_by_edge.keys()

        # Connect targets and sinks on edges
        for edge in edges:
            left, right = edge
            s_qubit, s_row = graph.qubit(left), graph.row(left)
            t_qubit, t_row = graph.qubit(right), graph.row(right)

            target_ids = self._targets_by_edge.get(edge) or []
            extra_nodes = [target_nodes[target_id] for target_id in target_ids]
            if edge in self._sinks_by_edge:
                extra_nodes.append(nodes.sinks[self._sinks_by_edge[edge]].gate)

            etab = dict()
            last_was_x_target = False
            def _append(index: int, is_x_target: bool):
                nonlocal left, last_was_x_target

                node = extra_nodes[index]
                # Position node
                graph.set_qubit(node, s_qubit + (t_qubit - s_qubit) * ((float(index) + 1) / (len(extra_nodes) + 1)))
                graph.set_row(node, s_row + (t_row - s_row) * ((float(index) + 1) / (len(extra_nodes) + 1)))

                # Connect to neighbours
                h_edge = is_x_target ^ last_was_x_target
                last_was_x_target = is_x_target
                etab[(left, node)] = (not h_edge, h_edge)
                left = node

            for idx, target_id in enumerate(target_ids):
                target = self._targets[target_id]
                _append(idx, is_x_target=target.type == TargetType.X)

                # Register neighbours with target node information
                gadget_id = self._in_gadget[target_id]
                if gadget_id not in nodes.targets: nodes.targets[gadget_id] = []
                nodes.targets[gadget_id].append(target_nodes[target_id])

            if edge in self._sinks_by_edge:
                _append(len(extra_nodes) - 1, is_x_target=False)

            etab[(left, right)] = (not last_was_x_target, last_was_x_target)

            graph.remove_edge(edge)
            graph.add_edge_table(etab)
            nodes.extra_nodes_by_edge[edge] = extra_nodes

        # Adjust gadget positions
        for gadget in self._gadgets.values():
            rows = [graph.row(target_nodes[target.id]) for target in gadget.targets]
            avg_row = sum(rows) / len(gadget.targets)
            graph.set_row(nodes.gadgets[gadget.id].dist, avg_row)
            graph.set_row(nodes.gadgets[gadget.id].spawn, avg_row)

        # Adjust sink end positions
        for edge, sink_id in self._sinks_by_edge.items():
            n1_qubit, n1_row = graph.qubit(edge[0]), graph.row(edge[0])
            n2_qubit, n2_row = graph.qubit(edge[1]), graph.row(edge[1])
            gate, end = nodes.sinks[sink_id]
            n3_qubit, n3_row = graph.qubit(gate), graph.row(gate)

            n4_normaliser = math.sqrt((n1_row - n2_row) ** 2 + (n1_qubit - n2_qubit) ** 2)
            n4_qubit = n3_qubit + (n1_row - n2_row) / (2 * n4_normaliser)
            n4_row = n3_row + (n1_qubit - n2_qubit) / (2 * n4_normaliser)
            graph.set_qubit(end, n4_qubit), graph.set_row(end, n4_row)

        return graph, nodes
