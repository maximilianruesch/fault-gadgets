import random
from functools import partial
from timeit import timeit

random.seed(50)

from dongle import expand_all_dongles, ShieldedGraph
import pyzx as zx

def _expand(g: ShieldedGraph):
    expand_all_dongles(g)
    g.full_instance()

def run():
    g = zx.generate.cnots(4, 5)
    zx.id_simp(g)

    bg = ShieldedGraph.from_graph(g)
    bg.add_all_dongles()

    print(timeit(partial(_expand, bg), globals=globals(), number=1))

if __name__ == "__main__":
    run()
