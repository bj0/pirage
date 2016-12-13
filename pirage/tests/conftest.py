import pytest
def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true",
        help="run slow tests")

def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getoption("--runslow"):
            pytest.skip("need --runslow option to run")

def pytest_ignore_collect(path, config):
    '''
    ignore obsolete tests for obsolete code
    '''
    return ('dweet' in path.basename
            or 'mqtt' in path.basename
            or '_fastsleep' in path.basename)
