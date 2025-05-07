from dongle import ShieldedGraph, Dongle, AdjPauliWeb, DongleTargetType, compute_webs_for_dongle
from pyzx import VertexType


def _ignore_dongle_internals(g: ShieldedGraph, web: AdjPauliWeb) -> AdjPauliWeb:
    new_web = web.copy()
    for dongle in g.dongles():
        new_web.es.pop((dongle.spawn, dongle.dist), '')
        new_web.es.pop((dongle.dist, dongle.spawn), '')

        for target in dongle.targets:
            new_web.es.pop((dongle.dist, target.get_id()), '')
            for n in g.neighbors(target.get_id()):
                new_web.es.pop((target.get_id(), n), '')

    return new_web

def fire_web_onto_dongle(g: ShieldedGraph, dongle: Dongle, web: AdjPauliWeb) -> None:
    new_web = _ignore_dongle_internals(g, web)
    for edge, pauli in new_web.half_edges().items():
        if g.type(edge[0]) == VertexType.BOUNDARY:
            continue

        new_edge = g._on_edge.get(edge[0]) or g._on_edge.get(edge[1]) or edge
        if pauli == 'X' or pauli == 'Y':
            g.add_target(DongleTargetType.X, dongle=dongle, edge=new_edge)
        elif pauli == 'Z' or pauli == 'Y':
            g.add_target(DongleTargetType.Z, dongle=dongle, edge=new_edge)


def expand_all_dongles(g: ShieldedGraph) -> None:
    for dongle in g.dongles():
        webs = compute_webs_for_dongle(g, dongle)
        if len(webs) == 0:
            raise AssertionError(f"No webs found for dongle {dongle}!")

        min_web = min(webs, key=lambda web: sum([1 if pauli != 'I' else 0 for pauli in web.half_edges().values() ]))
        fire_web_onto_dongle(g, dongle, min_web)
