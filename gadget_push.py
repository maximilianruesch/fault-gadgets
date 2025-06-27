from faultgadget import GadgetGraph, add_sinks_for_all_detecting_regions, add_all_gadgets, compute_webs_for_gadgets
import generate

def main():

    og = generate.zweb(3, 3)
    g = GadgetGraph.from_graph(og)

    add_sinks_for_all_detecting_regions(g)
    add_all_gadgets(g)
    gc, _ = g.realise()
    gc.pack_circuit_rows()
    gc.pack_circuit_qubits()

    compute_webs_for_gadgets(g, g.gadgets().keys())

if __name__ == "__main__":
    main()
