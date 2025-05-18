import random
from timeit import timeit

from pyzx.editor_actions import match_hadamard_edge
from pyzx.hrules import had_edge_to_hbox

random.seed(50)

from dongle import expand_all_dongles, DongleGraph
import pyzx as zx

def _expand(g: DongleGraph):
    expand_all_dongles(g)

def run_cnot():
    g = zx.generate.cnots(4, 5)
    zx.id_simp(g)

    bg = DongleGraph.from_graph(g)
    bg.add_all_dongles()

    # print(timeit(lambda: _expand(bg), globals=globals(), number=1))
    _expand(bg)

def run_clifford():
    g = zx.generate.cliffords(4, 7)
    zx.clifford_simp(g, quiet=True)
    g.normalize()
    for e in match_hadamard_edge(g):
        had_edge_to_hbox(g, e)

    bg = DongleGraph.from_graph(g)
    bg.add_all_dongles()

    # print(timeit(lambda: _expand(bg), globals=globals(), number=1))
    _expand(bg)

if __name__ == "__main__":
    run_cnot()
    run_clifford()
