import unittest.mock


class AsyncMock(unittest.mock.Mock):
    """
    Asynchronous Mock.  Calling this mock returns a coroutine.
    """
    def __call__(self, *args, **kwargs):
        async def coro():
            return super().__call__(*args, **kwargs)

        return coro()

    def __await__(self):
        return self().__await__()
