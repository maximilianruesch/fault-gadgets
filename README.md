# Fault gadgets for PyZX

A library to handle fault gadgets and associated computations including:
- Computing stabilisers and detecting regions of ZX-diagrams
- Determining signatures of faults
- Extracting the distance of a ZX-diagram
- Checking if a semantic-preserving ZX-rewrite is distance-preserving
- etc.

## Installation

1. Clone this repository
2. Clone [`zxcalc/pyzx`](https://github.com/zxcalc/pyzx) into `lib/pyzx`
3. Amend `lib/pyzx/pyzx/graph/graph_s.py` by changing the `clone` function to have this header:
    ```python
    def clone(self, instance: Optional['GraphS'] = None) -> 'GraphS':
        cpy = instance or GraphS()
    ```
4. Install this library with `pip install .` in the root directory, optionally with `--editable` if you want to make changes.

Then have fun figuring out the (unstable) API.
You could look at tests in `tests` for some hints on how they are used, or browse the files yourself.
