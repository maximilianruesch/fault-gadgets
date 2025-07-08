from typing import List, Mapping, Tuple, Dict, Iterable

from pyzx.graph.base import upair
from pyzx.graph.graph_s import GraphS
from ... import add_all_gadgets, GadgetGraph, add_sinks_for_all_detecting_regions, expand_all_gadgets
from ...pauli import Pauli

ET = Tuple[int, int]

class TannerGraph:
    def __init__(self, detectors: List[int], edge_pauli_to_detectors: Dict[Tuple[ET, Pauli], List[int]]):
        self.detectors = detectors
        self.edge_pauli_to_detectors = edge_pauli_to_detectors

    def get_violated_detectors(self, edge: ET, error_type: Pauli) -> Iterable[int]:
        return self.edge_pauli_to_detectors[edge, error_type]

    def get_detectors(self) -> Iterable[int]:
        return self.detectors

    def get_faults(self) -> Iterable[Tuple[ET, Pauli]]:
        return self.edge_pauli_to_detectors.keys()

    def get_undetected_faults(self) -> Iterable[Tuple[ET, Pauli]]:
        return [k for k, ds in self.edge_pauli_to_detectors.items() if len(ds) == 0]

# TODO could also construct tanner graph just from marking which detecting regions land where
def extract_tanner_graph(g: GraphS, quiet: bool = True) -> TannerGraph: # TODO test this function integratively
    gadget_graph = GadgetGraph.from_graph(g)
    add_sinks_for_all_detecting_regions(gadget_graph)
    edge_to_gadget_ids = add_all_gadgets(gadget_graph)
    # Theoretically we do not have to gadgets expand to boundaries fully, just need membership for sinks
    expand_all_gadgets(gadget_graph, quiet=quiet)

    sink_sigs_by_gadget_id: Mapping[int, List[int]] = {
        gadget_id: [
            gadget_graph.in_sink(target.id)
            for target in gadget.targets if gadget_graph.in_sink(target.id) is not None
        ]
        for gadget_id, gadget in gadget_graph.gadgets().items()
    }

    edge_pauli_to_sink_sigs: Dict[Tuple[ET, Pauli], List[int]] = dict()
    for edge, gadget_ids in edge_to_gadget_ids.items():
        x_gadget_id, z_gadget_id, y_gadget_id = gadget_ids
        edge_pauli_to_sink_sigs[upair(*edge), Pauli.X] = sink_sigs_by_gadget_id[x_gadget_id]

    return TannerGraph(list(gadget_graph.sinks().keys()), edge_pauli_to_sink_sigs)
