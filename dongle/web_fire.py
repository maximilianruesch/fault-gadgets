from dongle import ShieldedGraph, AdjPauliWeb, DongleTargetType, compute_web_for_dongle
from pyzx import VertexType


def _ignore_dongle_internals(g: ShieldedGraph, web: AdjPauliWeb) -> AdjPauliWeb:
    new_web = web.copy()
    for dongle in g.dongles().values():
        new_web.es.pop((dongle.spawn, dongle.dist), '')
        new_web.es.pop((dongle.dist, dongle.spawn), '')

        for target in dongle.targets:
            new_web.es.pop((dongle.dist, target.get_id()), '')
            for n in g.neighbors(target.get_id()):
                new_web.es.pop((target.get_id(), n), '')

    return new_web

def fire_web_onto_dongle(g: ShieldedGraph, dongle_id: int, web: AdjPauliWeb, quiet: bool = True) -> None:
    new_web = _ignore_dongle_internals(g, web)
    for edge, pauli in new_web.half_edges().items():
        if g.type(edge[0]) == VertexType.BOUNDARY:
            continue

        new_edge = g._on_edge.get(edge[0]) or g._on_edge.get(edge[1]) or edge
        if pauli == 'X' or pauli == 'Y':
            if not quiet:
                print(f"Firing X onto {new_edge} for dongle #{dongle_id} (from web edge: {edge})")
            g.add_target(DongleTargetType.X, dongle_id=dongle_id, edge=new_edge)
        elif pauli == 'Z' or pauli == 'Y':
            if not quiet:
                print(f"Firing Z onto {new_edge} for dongle #{dongle_id} (from web edge: {edge})")
            g.add_target(DongleTargetType.Z, dongle_id=dongle_id, edge=new_edge)


def expand_all_dongles(g: ShieldedGraph, quiet: bool = True) -> None:
    for dongle_id, dongle in g.dongles().items():
        web = compute_web_for_dongle(g, dongle_id)
        fire_web_onto_dongle(g, dongle_id, web, quiet=quiet)
        g.merge_targets(quiet=quiet)
        g.reassign_dongle_positions()
