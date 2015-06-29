import shelve
import tempfile, shutil
from contextlib import contextmanager

@contextmanager
def shelf(path):
    s = shelve.open(path)
    yield s
    s.close()

@contextmanager
def tempdir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
