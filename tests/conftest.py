import pytest


def pytest_addoption(parser):
    parser.addoption('--longrun', action='store_true', dest="longrun",
                 default=False, help="Enable longrun decorated tests")

longrun = pytest.mark.skipif("not config.getoption('longrun')")
