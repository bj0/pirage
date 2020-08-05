import asyncio as aio
from collections import deque

from .errors import *


class BufferedChannel(object):
    """
        A Channel is a closable queue. A Channel is considered "finished" when
        it is closed and drained (unlike a queue which is "finished" when the queue
        is empty)
    """

    def __init__(self, maxsize=0, *, loop=None):
        if loop is None:
            self._loop = aio.get_event_loop()
        else:
            self._loop = loop

        if not isinstance(maxsize, int) or maxsize < 0:
            raise TypeError("maxsize must be an integer >= 0 (deafult is 0)")
        self._maxsize = maxsize

        # Futures.
        self._getters = deque()
        self._putters = deque()

        # "finished" means channel is closed and drained
        self._finished = aio.Event(loop=self._loop)
        self._close = aio.Event(loop=self._loop)

        self._init()

    def _init(self):
        self._queue = deque()

    def _get(self):
        return self._queue.popleft()

    def _put(self, item):
        self._queue.append(item)

    @staticmethod
    def _wakeup_next(waiters):
        # Wake up the next waiter (if any) that isn't cancelled.
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def __repr__(self):
        return '<{} at {:#x} maxsize={!r} qsize={!r}>'.format(
            type(self).__name__, id(self), self._maxsize, self.qsize)

    def __str__(self):
        return '<{} maxsize={!r} qsize={!r}>'.format(
            type(self).__name__, self._maxsize, self.qsize)

    @property
    def qsize(self):
        """Number of items in the channel buffer."""
        return len(self._queue)

    @property
    def maxsize(self):
        """Number of items allowed in the channel buffer."""
        return self._maxsize

    @property
    def empty(self):
        """Return True if the channel is empty, False otherwise."""
        return not self._queue

    @property
    def full(self):
        """Return True if there are maxsize items in the channel.
        Note: if the Channel was initialized with maxsize=0 (the default),
        then full() is never True.
        """
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize >= self._maxsize

    async def send(self, item):
        """Put an item into the channel.
        If the channel is full, wait until a free
        slot is available before adding item.
        If the channel is closed or closing, raise ChannelClosed.
        This method is a coroutine.
        """
        while self.full and not self.closed:
            putter = aio.Future(loop=self._loop)
            self._putters.append(putter)
            try:
                await putter
            except ChannelClosed:
                raise
            except Exception:
                putter.cancel()  # Just in case putter is not done yet.
                if not self.full and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise
        self.offer(item)

    def offer(self, item):
        """Put an item into the channel without blocking.
        If no free slot is immediately available, raise ChannelFull.
        """
        if self.full:
            raise ChannelFull
        if self.closed:
            raise ChannelClosed
        self._put(item)
        self._wakeup_next(self._getters)

    async def receive(self):
        """Remove and return an item from the channel.
        If channel is empty, wait until an item is available.
        This method is a coroutine.
        """
        while self.empty and not self.closed:
            getter = aio.Future(loop=self._loop)
            self._getters.append(getter)
            try:
                await getter
            except ChannelClosed:
                raise
            except Exception:
                getter.cancel()  # Just in case getter is not done yet.
                if not self.empty and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters)
                raise
        return self.poll()

    def poll(self):
        """Remove and return an item from the channel.
        Return an item if one is immediately available, else raise ChannelEmpty.
        """
        if self.empty:
            if self.closed:
                raise ChannelClosed
            else:
                raise ChannelEmpty
        item = self._get()
        if self.empty and self.closed:
            # if empty _after_ we retrieved an item AND marked for closing,
            # set the finished flag
            self._finished.set()
        self._wakeup_next(self._putters)
        return item

    async def join(self):
        """Block until channel is closed and channel is drained
        """
        await self._finished.wait()

    def close(self):
        """Marks the channel is closed and throw a ChannelClosed in all pending putters"""
        self._close.set()
        # cancel putters
        for putter in self._putters:
            putter.set_exception(ChannelClosed())
        # cancel getters that can't ever return (as no more items can be added)
        while len(self._getters) > self.qsize:
            getter = self._getters.pop()
            getter.set_exception(ChannelClosed())

        if self.empty:
            # already empty, mark as finished
            self._finished.set()

    @property
    def closed(self):
        """Returns True if the Channel is marked as closed"""
        return self._close.is_set()

    async def __aiter__(self):  # pragma: no cover
        """Returns an async iterator (self)"""
        return self

    async def __anext__(self):  # pragma: no cover
        try:
            data = await self.receive()
        except ChannelClosed:
            raise StopAsyncIteration
        else:
            return data

    def __iter__(self):
        return iter(self._queue)
