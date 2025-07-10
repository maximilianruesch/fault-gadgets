# Fault gadgets for PyZX

A library to handle fault gadgets and associated computations including:
- Computing stabilisers and detecting regions of ZX-diagrams
- Determining signatures of faults
- Extracting the distance of a ZX-diagram
- Checking if a ZX-rewrite is fault-equivalent
- etc.

## Installation

The project requires at least Python version `>= 3.12`.
It is recommended that you use e.g. `conda` to create an isolated environment, so e.g.
```shell
conda create --name "faultgadgets" python=3.12
conda activate "faultgadgets"
```

1. Clone this repository and change into the directory of this file
2. Clone [`zxcalc/pyzx`](https://github.com/zxcalc/pyzx) into `lib/pyzx`
3. Amend `lib/pyzx/pyzx/graph/graph_s.py` by changing the `clone` function to have this header:
    ```python
    def clone(self, instance: Optional['GraphS'] = None) -> 'GraphS':
        cpy = instance or GraphS()
    ```
4. Install this library with `pip install -r requirements.txt -e .` in the root directory.

If you do not want to make any changes in the library, you may also omit the "-e" flag in the last command.

Then have fun figuring out the (unstable) API.
You could look at tests in `tests` for some hints on how they are used, or browse the files yourself.

## Running tests
Before running tests for the first time, you need to install the (usually optional) dependencies.
For this, simply run
```shell
pip install --group test
```

Afterwards (or if you already installed those dependencies), run
```shell
pytest
```
in the main directory.

If you encounter difficulties running the tests, make sure your installed packages are up to date and that you have all the packages listed in the `pyproject.toml`.
