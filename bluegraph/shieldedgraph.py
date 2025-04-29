from typing import Tuple, Dict, Iterable, Literal, List, Optional, Union

from pyzx.hsimplify import hadamard_simp
from .dongles import Dongle, DongleTarget, DongleTargetType, SlimDongle
from pyzx import EdgeType, VertexType
from pyzx.graph.graph_s import GraphS

class ShieldedGraph(GraphS):
    def __init__(self) -> None:
        GraphS.__init__(self)
        self._target_id_index = 0 # Counter which ID to assign to next target
        self._targets: Dict[int, DongleTarget] = dict() # ID target ID -> Target
        self._main_nodes: Dict[int, int] = dict() # target ID -> ID (target main node)
        self._in_dongle: Dict[int, Union[Dongle, SlimDongle]] = dict() # target ID -> Dongle of target
        self._on_edge: Dict[int, Tuple[int, int]] = dict() # target ID -> edge the target is on

    def clone(self, instance: Optional['ShieldedGraph'] = None) -> 'ShieldedGraph':
        cpy = GraphS.clone(self, instance)
        cpy._target_id_index = self._target_id_index
        cpy._targets = self._targets.copy()
        cpy._main_nodes = self._targets.copy()
        cpy._in_dongle = self._in_dongle.copy()
        cpy._on_edge = self._on_edge.copy()

        return cpy

    @staticmethod
    def from_graph(graph: GraphS) -> 'ShieldedGraph':
        """
        Assumes that the given graph has no shielded-edge or dongle information attached.
        """
        return graph.clone(ShieldedGraph())

    def _set_on_edge(self, target_ids: Iterable[int], edge: Tuple[int, int]) -> None:
        for target_id in target_ids:
            self._on_edge[target_id] = edge

    def _get_targets_by_edge(self) -> Dict[Tuple[int, int], List[DongleTarget]]:
        targets_by_edge: Dict[Tuple[int, int], List[DongleTarget]] = dict()
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

    def add_dongles(self, edge: Tuple[int, int]) -> Tuple[SlimDongle, SlimDongle, SlimDongle]:
        edge_type = self.edge_type(edge)
        if edge_type == 0:
            raise ValueError('Edge to convert is not in graph!')
        elif not edge_type == EdgeType.SIMPLE:
            raise ValueError('Edge to convert must be a simple edge!')
        elif edge in self._on_edge.values() or (edge[0], edge[1]) in self._on_edge.values():
            raise ValueError('Edge to populate is already populated!')

        x_dongle = self._add_dongle(types=['X'])
        x_target = x_dongle.targets[0].get_id()
        z_dongle = self._add_dongle(types=['Z'])
        z_target = z_dongle.targets[0].get_id()
        y_dongle = self._add_dongle(types=['Y'])
        y_target_1, y_target_2 = y_dongle.targets[0].get_id(), y_dongle.targets[1].get_id()
        self._set_on_edge([x_target, z_target, y_target_1, y_target_2], edge)

        return x_dongle, z_dongle, y_dongle

    def _add_dongle(self, types: Iterable[Literal['X', 'Y', 'Z']]) -> SlimDongle:
        targets = []
        for target_type in types:
            if target_type == 'X' or target_type == 'Y':
                targets.append(self._add_target(DongleTargetType.X))
            if target_type == 'Z' or target_type == 'Y':
                targets.append(self._add_target(DongleTargetType.Z))
        dongle = SlimDongle(self, targets)
        for target in targets:
            self._in_dongle[target.get_id()] = dongle
        return dongle

    def _add_target(self, _type: DongleTargetType) -> DongleTarget:
        _id = self._target_id_index
        self._target_id_index += 1

        _target = DongleTarget(_id=_id, _type=_type)
        self._targets[_id] = _target

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

    def merge_all_targets(self) -> None:
        for dongle in set(self._in_dongle.values()):
            x_targets_by_edge: Dict[Tuple[int, int], List[DongleTarget]] = dict()
            z_targets_by_edge: Dict[Tuple[int, int], List[DongleTarget]] = dict()
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
        for edge, targets in self._get_targets_by_edge().items():
            if self.edge_type(edge) == 0:
                raise ValueError('Edge to instance on is not in graph, maybe targets were already instantiated on it?')

            left, right = edge
            self.remove_edge(edge)
            for target in targets:
                slim_dongle = self._in_dongle[target.get_id()]
                if slim_dongle not in dongles_instanced:
                    # Instance dongle
                    spawn = self.add_vertex(VertexType.Z, qubit=-4, row=1.2)
                    dist = self.add_vertex(VertexType.X, qubit=-3, row=1.2)
                    self.add_edge((spawn, dist), edgetype=EdgeType.SIMPLE)
                    dongles_instanced[slim_dongle] = Dongle.from_slim(slim_dongle, spawn, dist)

                # Instance target itself
                _main_node = self.add_vertex(VertexType.Z_BOX, qubit=-1, row=1.7) # TODO choose a more appropriate node type
                self._main_nodes[target.get_id()] = _main_node
                self._in_dongle[target.get_id()] = dongles_instanced[slim_dongle]
                self.add_edges([
                    (dongles_instanced[slim_dongle].distributor_node, _main_node),
                    (left, _main_node),
                ])
                left = _main_node
            self.add_edge((left, right))

    ###########################################################
    #                       Realising                         #
    ###########################################################

    def realise_all_targets(self, h_edges=False) -> None:
        hadamards = []
        for edge, targets in self._get_targets_by_edge().items():
            # Connect all lefts and rights
            left, right = edge
            new_edges = []
            for target in targets:
                _id = target.get_id()
                self.remove_vertex(self._main_nodes[_id])
                dongle = self._in_dongle[_id]
                if target.get_type() == DongleTargetType.X:
                    hadamard_left = self.add_vertex(VertexType.H_BOX, qubit=-1, row=1.7)
                    new_node = self.add_vertex(VertexType.Z, qubit=-1, row=1.8)
                    hadamard_right = self.add_vertex(VertexType.H_BOX, qubit=-1, row=1.9)
                    hadamards.extend([hadamard_left, hadamard_right])
                    new_edges.extend([
                        (hadamard_left, new_node),
                        (dongle.distributor_node, new_node),
                        (new_node, hadamard_right),
                        (left, hadamard_left),
                    ])
                    left = hadamard_right
                elif target.get_type() == DongleTargetType.Z:
                    new_node = self.add_vertex(VertexType.Z, qubit=-1, row=1.6)
                    self.add_edges([
                        (dongle.distributor_node, new_node),
                        (left, new_node),
                    ])
                    left = new_node
                else:
                    raise RuntimeError(f"Unexpected target type: {target.get_type()}")

            self.add_edge((left, right))

        if h_edges:
            hadamard_simp(self, matchf=lambda h: h in hadamards)

    ###########################################################
    #                       Pushing                           #
    ###########################################################

    def push_target(self, target: DongleTarget, new_edge: Tuple[int, int]) -> None:
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

        def _multiply_through(_type: DongleTargetType):
            dongle = self._in_dongle[_id]
            for e1, e2 in list(self.edges(gateway)):
                other = e1 if gateway == e2 else e2
                if other == co_gateway:
                    continue # Skip the edge that the target is pushed from

                new_target = self._add_target(_type)
                dongle.targets.append(new_target)
                self._in_dongle[new_target.get_id()] = dongle
                self._on_edge[new_target.get_id()] = (e1, e2)

            self._remove_target(target)

        if gateway_type == VertexType.Z:
            if target.get_type() == DongleTargetType.Z:
                self._on_edge[_id] = new_edge
            else:
                _multiply_through(DongleTargetType.X)
        elif gateway_type == VertexType.X:
            if target.get_type() == DongleTargetType.X:
                self._on_edge[_id] = new_edge
            else:
                _multiply_through(DongleTargetType.Z)
        elif gateway_type == VertexType.H_BOX:
            self._on_edge[_id] = new_edge
            target.set_type(target.get_type().flip())
        else:
            raise NotImplementedError(f"Gateway type {gateway_type.name} unhandled right now!")
