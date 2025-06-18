from .dongles import DongleTargetType
from .graph import DongleGraph
from .web import Pauli
from .dongle_web_compute import compute_webs_for_dongles, DonglePauliWeb
from pyzx import VertexType

def fire_web_onto_dongle(g: DongleGraph, dongle_id: int, web: DonglePauliWeb, quiet: bool = True) -> None:
    for edge, pauli in web.meta_half_edges.items():
        if g.type(edge[0]) == VertexType.BOUNDARY:
            continue

        if pauli == Pauli.X or pauli == Pauli.Y:
            if not quiet: print(f"Firing X onto {edge} for dongle #{dongle_id} (from web edge: {edge})")
            g.add_target(DongleTargetType.X, dongle_id=dongle_id, edge=edge)
        elif pauli == Pauli.Z or pauli == Pauli.Y:
            if not quiet: print(f"Firing Z onto {edge} for dongle #{dongle_id} (from web edge: {edge})")
            g.add_target(DongleTargetType.Z, dongle_id=dongle_id, edge=edge)

def expand_all_dongles(g: DongleGraph, quiet: bool = True) -> None:
    if not quiet:
        print(f"Expanding {len(g.dongles())} dongles!")
    webs = compute_webs_for_dongles(g, g.dongles().keys())
    for dongle_id in g.dongles().keys():
        fire_web_onto_dongle(g, dongle_id, webs[dongle_id], quiet=quiet)
    g.merge_targets(quiet=quiet)