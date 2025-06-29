from pyzx import VertexType
from pyzx.graph.graph_s import GraphS
from ...graph_helpers import add_sinks_for_all_detecting_regions
from ...gadget_web_fire import expand_all_gadgets
from ...graph import GadgetGraph
from ...web import compute_stabilisers
from .enumeration import _smallest_size_iteration, _calculate_signature_normal_forms

def _add_gadgets(dg: GadgetGraph) -> int:
    num_gadgets_added = 0
    for edge in list(dg.edges()):
        # Gadgets on inputs and outputs do not change for rewrites, thus skip
        if dg.type(edge[0]) is VertexType.BOUNDARY or dg.type(edge[1]) is VertexType.BOUNDARY:
            continue

        dg.add_edge_flip_gadgets(edge)
        num_gadgets_added += 3

    return num_gadgets_added

def is_distance_preserving(g1: GraphS, g2: GraphS, quiet: bool = True) -> bool:
    if not quiet: print("Computing stabilisers...")
    stabilisers = compute_stabilisers(g1) # TODO if strict, compute stabilisers of g2 and assert space equality

    if not quiet: print("Constructing signatures of g1...")
    gg1 = GadgetGraph.from_graph(g1)
    gg1_num_sinks = add_sinks_for_all_detecting_regions(gg1)
    _add_gadgets(gg1)
    expand_all_gadgets(gg1, quiet=quiet)
    g1_sig_nf = _calculate_signature_normal_forms(gg1, stabilisers)

    if not quiet: print("Constructing signatures of g2...")
    gg2 = GadgetGraph.from_graph(g2)
    gg2_num_sinks = add_sinks_for_all_detecting_regions(gg2)
    _add_gadgets(gg2)
    expand_all_gadgets(gg2, quiet=quiet)
    g2_sig_nf = _calculate_signature_normal_forms(gg2, stabilisers)

    if not quiet: print("Checking if g1 -> g2 is distance non-decreasing...")
    g1_g2_weight = _smallest_size_iteration(g1_sig_nf, g2_sig_nf, gg1_num_sinks, gg2_num_sinks, quiet=quiet)
    if g1_g2_weight is not None:
        return False

    if not quiet: print("Checking if g2 -> g1 is distance non-decreasing...")
    g2_g1_weight = _smallest_size_iteration(g2_sig_nf, g1_sig_nf, gg2_num_sinks, gg1_num_sinks, quiet=quiet)
    return g2_g1_weight is None
