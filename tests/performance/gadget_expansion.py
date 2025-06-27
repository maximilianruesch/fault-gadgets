import random
from timeit import timeit

from pyzx.editor_actions import match_hadamard_edge
from pyzx.hrules import had_edge_to_hbox

random.seed(50)

from faultgadget import expand_all_gadgets, GadgetGraph, add_all_gadgets
import pyzx as zx

def _expand(g: GadgetGraph):
    expand_all_gadgets(g)

def run_cnot():
    g = zx.generate.cnots(4, 5)
    zx.id_simp(g)

    bg = GadgetGraph.from_graph(g)
    add_all_gadgets(bg)

    print(timeit(lambda: _expand(bg), globals=globals(), number=1))

def run_clifford():
    g = zx.generate.cliffords(4, 7)
    zx.clifford_simp(g, quiet=True)
    g.normalize()
    for e in match_hadamard_edge(g):
        had_edge_to_hbox(g, e)

    bg = GadgetGraph.from_graph(g)
    add_all_gadgets(bg)

    print(timeit(lambda: _expand(bg), globals=globals(), number=1))

if __name__ == "__main__":
    run_cnot()
    run_clifford()
