import asyncio as aio
import inspect
import shelve
import tempfile, shutil
from contextlib import contextmanager


@contextmanager
def shelf(path):
    """
    Contextmanager for shelve.open
    """
    s = shelve.open(path)
    yield s
    s.close()


@contextmanager
def tempdir():
    """
    Contextmanager for tempfile.mkdtemp
    """
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


class AttrDict(dict):
    """
    dict subclass that adds attribute access for keys.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


class AsyncGenerator:
    """
    Class decorator that turns a coroutine into an async iterator.

    The decorated coroutine will take a special 'put' function in addition
    to it's normal arguments, this is used to 'push' data out the iterator.
    """

    def __init__(self, f):
        self.f = f

    async def put(self, ret):
        """
        Used by decorated coroutine to push data out the iterator.
        """
        await self.q.put(ret)
        await self.q.join()

    def __call__(self, *args, **kwargs):
        """
        Creates an instance of this class that contains all the per-call state.
        """
        inst = AsyncGenerator(self.f)
        inst.q = aio.Queue()
        inst.args = args
        inst.kwargs = kwargs
        return inst

    async def __aiter__(self):
        """
        Schedules the wrapped coroutine and returns self.
        """
        self.task = aio.ensure_future(self.f(self.put, *self.args, **self.kwargs))
        return self

    async def __anext__(self):
        """
        Wait for data to be pushed from the wrapped coroutine or for it
        to finish executing.  The result is returned or StopAsyncIteration is
        raised.
        """
        qtask = aio.ensure_future(self.q.get())
        done, pending = await aio.wait((self.task, qtask), return_when=aio.FIRST_COMPLETED)
        if qtask.done():
            self.q.task_done()
            return qtask.result()

        # coroutine is done, stop waiting for data
        qtask.cancel()
        raise StopAsyncIteration


class AsyncIterator:
    def __init__(self, iterator):
        self.iter = iterator

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            yielded = next(self.iter)
            while inspect.isawaitable(yielded):
                try:
                    result = await yielded
                except Exception as e:
                    yielded = self.iter.throw(e)
                else:
                    yielded = self.iter.send(result)
            else:
                return yielded
        except StopIteration:
            raise StopAsyncIteration


def asynciter(f):
    return lambda *args, **kwargs: AsyncIterator(f(*args, **kwargs))
