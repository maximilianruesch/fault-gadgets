def main():
    from dongle import DongleGraph, generate, compute_detecting_regions, compute_webs_for_dongles

    og = generate.zweb(3, 3)
    g = DongleGraph.from_graph(og)

    g.add_sinks_for_detecting_regions(compute_detecting_regions(og))
    g.add_all_dongles()
    gc = g.clone(DongleGraph())
    gc.reassign_dongle_positions()
    gc.pack_circuit_rows()
    gc.pack_circuit_qubits()
    gc.realise_all_targets()

    compute_webs_for_dongles(g, g.dongles().keys())

if __name__ == "__main__":
    main()
