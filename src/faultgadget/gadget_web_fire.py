from .gadget import TargetType
from .graph import GadgetGraph
from .web import Pauli
from .gadget_web_compute import compute_webs_for_gadgets, GadgetPauliWeb
from pyzx import VertexType

def fire_web_onto_gadget(g: GadgetGraph, gadget_id: int, web: GadgetPauliWeb, quiet: bool = True) -> None:
    for edge, pauli in web.meta_half_edges.items():
        if g.type(edge[0]) == VertexType.BOUNDARY:
            continue

        if pauli == Pauli.X or pauli == Pauli.Y:
            if not quiet: print(f"Firing X onto {edge} for gadget #{gadget_id} (from web edge: {edge})")
            g.add_target_on_edge(TargetType.X, gadget_id=gadget_id, edge=edge)
        elif pauli == Pauli.Z or pauli == Pauli.Y:
            if not quiet: print(f"Firing Z onto {edge} for gadget #{gadget_id} (from web edge: {edge})")
            g.add_target_on_edge(TargetType.Z, gadget_id=gadget_id, edge=edge)

    for sink_id in web.z_sinks:
        if not quiet: print(f"Firing Z into sink {sink_id} for gadget #{gadget_id}")
        g.add_target_in_sink(TargetType.Z, gadget_id=gadget_id, sink_id=sink_id)
        # Effectively remove target that was moved from meta edge into sink
        g.add_target_on_edge(TargetType.Z, gadget_id=gadget_id, edge=g.sink_on_edge(sink_id))
    for sink_id in web.x_sinks:
        if not quiet: print(f"Firing X into sink {sink_id} for gadget #{gadget_id}")
        g.add_target_in_sink(TargetType.X, gadget_id=gadget_id, sink_id=sink_id)
        # Effectively remove target that was moved from meta edge into sink
        g.add_target_on_edge(TargetType.X, gadget_id=gadget_id, edge=g.sink_on_edge(sink_id))

def expand_all_gadgets(g: GadgetGraph, quiet: bool = True) -> None:
    if not quiet:
        print(f"Expanding {len(g.gadgets())} gadgets!")
    webs = compute_webs_for_gadgets(g, g.gadgets().keys())
    for gadget_id in g.gadgets().keys():
        fire_web_onto_gadget(g, gadget_id, webs[gadget_id], quiet=quiet)
    g.merge_targets(quiet=quiet)