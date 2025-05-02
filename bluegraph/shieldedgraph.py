from typing import Tuple, Dict, Iterable, Literal, List, Optional, Union

from pyzx.hsimplify import hadamard_simp
from .dongles import Dongle, DongleTarget, DongleTargetType, SlimDongle
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

ET = Tuple[int, int]

class ShieldedGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._target_id_index = 0 # Counter which ID to assign to next target
        self._targets: Dict[int, DongleTarget] = dict() # ID target ID -> Target
        self._main_nodes: Dict[int, int] = dict() # target ID -> ID (target main node)
        self._in_dongle: Dict[int, Union[Dongle, SlimDongle]] = dict() # target ID -> Dongle of target
        self._on_edge: Dict[int, ET] = dict() # target ID -> edge the target is on

    def clone(self, instance: Optional['ShieldedGraph'] = None) -> 'ShieldedGraph':
        cpy = GraphS.clone(self, instance)
        cpy._target_id_index = self._target_id_index
        cpy._targets = self._targets.copy() # TODO ensure this is a deep copy
        cpy._main_nodes = self._targets.copy()
        cpy._in_dongle = self._in_dongle.copy() # TODO ensure this is a deep copy
        cpy._on_edge = self._on_edge.copy()

        return cpy

    @staticmethod
    def from_graph(graph: GraphS) -> 'ShieldedGraph':
        """
        Assumes that the given graph has no dongle information attached.
        If a graph with dongles needs to be copied, use `clone` instead.
        """
        return graph.clone(ShieldedGraph())

    def _targets_by_edge(self) -> Dict[ET, List[DongleTarget]]:
        targets_by_edge: Dict[ET, List[DongleTarget]] = dict()
        for target_id, edge in self._on_edge.items():
            if edge not in targets_by_edge:
                targets_by_edge[edge] = []
            targets_by_edge[edge].append(self._targets[target_id])

        return targets_by_edge

    ###########################################################
    #                        Dongles                          #
    ###########################################################

    def add_all_dongles(self):
        if len(self._on_edge) != 0:
            raise ValueError(f"The graph already has some dongles!")

        for edge in list(self.edges()):
            self.add_dongles(edge)

    def add_dongles(self, edge: ET) -> Tuple[SlimDongle, SlimDongle, SlimDongle]:
        edge_type = self.edge_type(edge)
        if edge_type == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not edge_type == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')
        elif edge in self._on_edge.values() or (edge[0], edge[1]) in self._on_edge.values():
            raise ValueError('Edge to populate is already populated!')

        return (self._add_dongle(types=['X'], edge=edge),
                self._add_dongle(types=['Z'], edge=edge),
                self._add_dongle(types=['Y'], edge=edge))

    def _add_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']], edge: Optional[ET] = None) -> SlimDongle:
        dongle = SlimDongle(self, targets=[])
        for target_type in types:
            if target_type == 'X' or target_type == 'Y':
                self._add_target(DongleTargetType.X, dongle=dongle, edge=edge)
            if target_type == 'Z' or target_type == 'Y':
                self._add_target(DongleTargetType.Z, dongle=dongle, edge=edge)
        return dongle

    def _add_target(self, _type: DongleTargetType,
                    dongle: Optional[Union[Dongle,SlimDongle]] = None,
                    edge: Optional[ET] = None) -> DongleTarget:
        _id = self._target_id_index
        self._target_id_index += 1

        _target = DongleTarget(_id=_id, _type=_type)
        self._targets[_id] = _target

        if dongle is not None:
            dongle.targets.append(_target)
            self._in_dongle[_id] = dongle
        if edge is not None:
            self._on_edge[_id] = edge

        return _target

    def _remove_target(self, target: DongleTarget) -> None:
        _id = target.get_id()
        dongle = self._in_dongle[_id]
        dongle.targets.remove(target)

        del self._targets[_id]
        del self._in_dongle[_id]
        del self._on_edge[_id]

    def _remove_targets(self, targets: Iterable[DongleTarget]) -> None:
        for target in targets:
            self._remove_target(target)

    def merge_targets(self) -> None:
        for dongle in self._in_dongle.values():
            self.merge_targets_of_dongle(dongle)

    def merge_targets_of_dongle(self, dongle: Union[Dongle, SlimDongle]) -> None:
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

    ###########################################################
    #                       Instancing                        #
    ###########################################################

    def instance_all_dongles(self) -> None:
        dongles_instanced: Dict[SlimDongle, Dongle] = dict()
        for edge, targets in self._targets_by_edge().items():
            if self.edge_type(edge) == 0:
                raise ValueError('Edge to instance on is not in graph, maybe targets were already instantiated on it?')

            left, right = edge
            self.remove_edge(edge)
            for target in targets:
                slim_dongle = self._in_dongle[target.get_id()]
                if slim_dongle not in dongles_instanced:
                    # Instance dongle
                    spawn = self.add_vertex(VertexType.Z, qubit=-3)
                    dist = self.add_vertex(VertexType.X, qubit=-2)
                    self.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)
                    dongles_instanced[slim_dongle] = Dongle.from_slim(slim_dongle, spawn, dist)

                # Instance target itself
                _main_node = self.add_vertex(VertexType.Z_BOX) # TODO choose a more appropriate node type
                self._main_nodes[target.get_id()] = _main_node
                self._in_dongle[target.get_id()] = dongles_instanced[slim_dongle]
                self.add_edges([
                    (dongles_instanced[slim_dongle].distributor_node, _main_node),
                    (left, _main_node),
                ])
                left = _main_node
            self.add_edge((left, right), edgetype=EdgeType.SIMPLE)

    def adjust_all_dongle_positions(self):
        # Adjust all target positions
        for edge, targets in self._targets_by_edge().items():
            s,t = edge
            s_qubit, s_row = self.qubit(s), self.row(s)
            t_qubit, t_row = self.qubit(t), self.row(t)

            if s_qubit == t_qubit:  # Horizontal
                for idx, target in enumerate(targets):
                    main_node = self._main_nodes[target.get_id()]
                    self.set_qubit(main_node, s_qubit)
                    self.set_row(main_node,
                                 s_row + (t_row - s_row) * ((float(idx) + 1) / (len(targets) + 1)))
            elif s_row == t_row:  # Vertical
                for idx, target in enumerate(targets):
                    main_node = self._main_nodes[target.get_id()]
                    self.set_qubit(main_node,
                                   s_qubit + (t_qubit - s_qubit) * ((float(idx) + 1) / (len(targets) + 1)))
                    self.set_row(main_node, s_row)
            else:
                raise ValueError("Underlying diagram is not on a grid!")

        # Adjust all distributors and spawn rows
        for dongle in self._in_dongle.values():
            rows = [self.row(self._main_nodes[target.get_id()]) for target in dongle.targets]
            avg_row = sum(rows) / len(dongle.targets)
            self.set_row(dongle.distributor_node, avg_row)
            self.set_row(dongle.spawn_node, avg_row)

    ###########################################################
    #                       Realising                         #
    ###########################################################

    def realise_all_targets(self, h_edges=False) -> None:
        hadamards = []
        for edge, targets in self._targets_by_edge().items():
            # Connect all lefts and rights
            left, right = edge
            new_edges = []
            for target in targets:
                _id = target.get_id()
                main_node = self._main_nodes[_id]
                main_qubit, main_row = self.qubit(main_node), self.row(main_node)
                self.remove_vertex(main_node)
                dongle = self._in_dongle[_id]
                if target.get_type() == DongleTargetType.X:
                    hadamard_left = self.add_vertex(VertexType.H_BOX, qubit=main_qubit, row=main_row - 0.01)
                    new_node = self.add_vertex(VertexType.Z, qubit=main_qubit, row=main_row)
                    hadamard_right = self.add_vertex(VertexType.H_BOX, qubit=main_qubit, row=main_row + 0.01)
                    hadamards.extend([hadamard_left, hadamard_right])
                    self.add_edges([
                        (hadamard_left, new_node),
                        (dongle.distributor_node, new_node),
                        (new_node, hadamard_right),
                        (left, hadamard_left),
                    ])
                    left = hadamard_right
                elif target.get_type() == DongleTargetType.Z:
                    new_node = self.add_vertex(VertexType.Z, qubit=main_qubit, row=main_row)
                    self.add_edges([
                        (dongle.distributor_node, new_node),
                        (left, new_node),
                    ])
                    left = new_node
                else:
                    raise RuntimeError(f"Unexpected target type: {target.get_type()}")

            self.add_edge((left, right))

        if h_edges:
            hadamard_simp(self, matchf=lambda h: h in hadamards, quiet=True)

    def full_instance(self, h_edges=False) -> None:
        self.instance_all_dongles()
        self.adjust_all_dongle_positions()
        self.realise_all_targets(h_edges=h_edges)
        self.pack_circuit_rows()
        self.auto_detect_io()

    ###########################################################
    #                       Pushing                           #
    ###########################################################

    # TODO handle hadamard edges
    def push_target(self, target: DongleTarget, new_edge: ET) -> Iterable[DongleTarget]:
        """
        Push the target to the next edge which must be adjacent.
        May have side effects on the target / introduce new targets / remove target.
        """
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

        def _multiply_through(_type: DongleTargetType) -> Iterable[DongleTarget]:
            dongle = self._in_dongle[_id]
            new_targets = []
            for e1, e2 in list(self.edges(gateway)):
                other = e1 if gateway == e2 else e2
                if other != co_gateway: # Skip the edge that the target is pushed from
                    new_targets.append(self._add_target(_type, dongle=dongle, edge=(e1,e2)))
            self._remove_target(target)
            return new_targets

        if gateway_type == VertexType.Z:
            if target.get_type() == DongleTargetType.Z:
                self._on_edge[_id] = new_edge
                return [target]
            else:
                return _multiply_through(DongleTargetType.X)
        elif gateway_type == VertexType.X:
            if target.get_type() == DongleTargetType.X:
                self._on_edge[_id] = new_edge
                return [target]
            else:
                return _multiply_through(DongleTargetType.Z)
        elif gateway_type == VertexType.H_BOX:
            self._on_edge[_id] = new_edge
            target.set_type(target.get_type().flip())
            return [target]
        else:
            raise NotImplementedError(f"Gateway type {gateway_type.name} unhandled right now!")
