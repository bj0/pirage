import asyncio
import asyncio as aio
import inspect
import shelve
import shutil
import tempfile
from contextlib import contextmanager


# def create_task(coro):
#     """this should be DEPRECATED in 3.7, when this function will be added to asyncio"""
#     return asyncio.get_event_loop().create_task(coro)


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

#
# @DeprecationWarning
# class AsyncGenerator:
#     """
#     Class decorator that turns a coroutine into an async iterator.
#
#     The decorated coroutine will take a special 'put' function in addition
#     to it's normal arguments, this is used to 'push' data out the iterator.
#
#     DEPRECATED: no longer necessary in 3.6: https://docs.python.org/3.6/whatsnew/3.6.html#pep-525-asynchronous-generators
#
#     """
#
#     def __init__(self, f):
#         self.f = f
#
#     async def put(self, ret):
#         """
#         Used by decorated coroutine to push data out the iterator.
#         """
#         await self.q.put(ret)
#         await self.q.join()
#
#     def __call__(self, *args, **kwargs):
#         """
#         Creates an instance of this class that contains all the per-call state.
#         """
#         inst = AsyncGenerator(self.f)
#         inst.q = aio.Queue()
#         inst.args = args
#         inst.kwargs = kwargs
#         return inst
#
#     async def __aiter__(self):
#         """
#         Schedules the wrapped coroutine and returns self.
#         """
#         self.task = aio.ensure_future(self.f(self.put, *self.args, **self.kwargs))
#         return self
#
#     async def __anext__(self):
#         """
#         Wait for data to be pushed from the wrapped coroutine or for it
#         to finish executing.  The result is returned or StopAsyncIteration is
#         raised.
#         """
#         qtask = aio.ensure_future(self.q.get())
#         done, pending = await aio.wait((self.task, qtask), return_when=aio.FIRST_COMPLETED)
#         if qtask.done():
#             self.q.task_done()
#             return qtask.result()
#
#         # coroutine is done, stop waiting for data
#         qtask.cancel()
#         raise StopAsyncIteration
#
#
# @DeprecationWarning
# class AsyncIterator:
#     """DEPRECATED: no longer necessary after 3.6:
#     https://docs.python.org/3.6/whatsnew/3.6.html#pep-525-asynchronous-generators """
#
#     def __init__(self, iterator):
#         self.iter = iterator
#
#     async def __aiter__(self):
#         return self
#
#     async def __anext__(self):
#         try:
#             yielded = next(self.iter)
#             while inspect.isawaitable(yielded):
#                 try:
#                     result = await yielded
#                 except Exception as e:
#                     yielded = self.iter.throw(e)
#                 else:
#                     yielded = self.iter.send(result)
#             else:
#                 return yielded
#         except StopIteration:
#             raise StopAsyncIteration
#
#
# @DeprecationWarning
# def asynciter(f):
#     """DEPRECATED: no longer necessary after 3.6:
#     https://docs.python.org/3.6/whatsnew/3.6.html#pep-525-asynchronous-generators """
#     return lambda *args, **kwargs: AsyncIterator(f(*args, **kwargs))
