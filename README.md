# `faultgadgets` for PyZX

A library to handle faults, fault models and related constructions in ZX-diagrams including (but not limited to):
- Computing stabilisers and detecting regions
- Determining signatures of faults
- Extracting the distance of a ZX-diagram
- Checking if a ZX-rewrite is fault-equivalent
- etc.

Do note that the library is still in early development.
If you encounter any bugs, feel free to open an issue!

## Installation

The project requires at least Python version `>= 3.12`.
It is recommended that you use e.g. `conda` to create an isolated environment, so
```shell
conda create --name "faultgadgets" python=3.12
conda activate "faultgadgets"
```

1. Clone this repository and change into the directory of this file
2. Install this library with `pip install -e .` in the root directory.

If you do not want to make any changes in the library, you may also omit the "-e" flag in the last command.
Currently, the library depends on a slightly modified version of PyZX found under [`maximilianruesch/pyzx`](https://github.com/maximilianruesch/pyzx/tree/fault-gadget-support).
If for some reason this does not work for you, please read the section below.

### I want to use my own PyZX (or yours is outdated)

1. Uninstall the current pyzx package: `pip uninstall pyzx`
2. Obtain PyZX, e.g. via `git clone https://github.com/zxcalc/pyzx lib/pyzx`
3. Install PyZX as editable, e.g. via `pip install -e lib/pyzx`
4. Amend `lib/pyzx/pyzx/graph/graph_s.py` by changing the `clone` function to have this header:
    ```python
    def clone[T: GraphS](self, instance: Optional[T] = None) -> T:
        cpy = instance or GraphS()
    ```
There is ongoing work to make the use with PyZX easier, but sometimes patches are simply required.
This nuisance will be removed as soon as possible!

## Documentation
There is no documentation yet, but you may have a look into the `tests` directory to get a glimpse of how the package may be used, or browse the files yourself.

You may also want to look at the `demo` folder, where you will find a few notebooks highlighting the key features of this library.

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

## Acknowledging the use of `faultgadgets`
```bibtex
@misc{rüsch2025completenessfaultequivalenceclifford,
    title={Completeness for Fault Equivalence of Clifford ZX Diagrams},
    author={Maximilian Rüsch and Benjamin Rodatz and Aleks Kissinger},
    year={2025},
    eprint={2510.08477},
    archivePrefix={arXiv},
    primaryClass={quant-ph},
    url={https://arxiv.org/abs/2510.08477},
}
```
