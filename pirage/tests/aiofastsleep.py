import asyncio as aio
import pytest


class FastSleep(object):
    '''
    FastSleep patches asyncio.sleep so that every asyncio.sleep(N) becomes
    asyncio.sleep(0).  This effectively changes it to a no-wait context switch.
    The seconds passed to .sleep(N) are summed up and available from
    FastSleep.now.

    If sleep is imported with from asyncio import sleep, FastSleep can be used
    to patch it with::

    fastsleep.patch('module.sleep')
    '''
    def __init__(self, monkeypatch):
        self._monkey = monkeypatch
        self._real_sleep = aio.sleep
        self._current = 0

        self.patch('asyncio.sleep')

    @property
    def now(self):
        '''
        Return the sum of executed patched sleep calls.
        '''
        return self._current

    def patch(self, module):
        '''
        Patch a function with monkeypatch to call `fastsleep`, a no-wait context switch.
        '''
        self._monkey.setattr(module, self.fastsleep)

    async def fastsleep(self, dt=0):
        '''
        Add dt to running sum and .sleep(0) for a context switch.  This is the function
        patched into asyncio.sleep.
        '''
        self._current += dt
        await self._real_sleep(0)


class FancySleep(FastSleep):
    """
    FancySleep patches asyncio.sleep like FastSleep, but instead of simply
    replacing it with a context switch, FancySleep uses asyncio.Event
    to explicitly control the order of tasks resuming from .sleep.

    This allows FancySleep to control the execution order and "time" that
    tasks are resumed from .sleep.  The "time", tracked by .now, can be
    advanced manually with::

    await fancysleep.step(N)

    or automatically.  Stepping advances to each
    Event added by .sleep until it reaches the .step time or runs out of Events.

    **WARNING:** Since FancySleep uses aio.Event to effectively lock
    a greenthread until itself releases it, simply calling aio.sleep in the
    "main" task will deadlock .
    To prevent his from happening there are two options:

     1) Make sure any code that uses aio.sleep is executed in a separate
     task.  This can be done by wrapping code in aio.ensure_future.  The main
     task can then use .step to manually advance, unlocking the sleeping
     tasks.

     2) *RECOMMENDED:* Enable automatic stepping by calling .start on fancysleep
     before executing any code that uses aio.sleep.  This will spawn a
     task that automatically steps to the next Event whenever the main
     task switches its context.  This allows manually stepping through
     "time" using either .step OR aio.sleep in the main task.  This
     auto-stepping task will run until explicitly stopped with .stop.

    To advance automatically, start FancySleep before calling code that uses
    aio.sleep, and stop it after::

    fancysleep.start()
    await aio.sleep(100)
    await function_that_sleeps()
    fancysleep.stop()

    Alternatively, FancySleep can be used as a context manager to automatically
    start and stop it's automatic stepping::

    with fancysleep:
        await aio.sleep(100)
        await function_that_sleeps()

    """
    def __init__(self, monkeypatch):
        super(FancySleep, self).__init__(monkeypatch)
        self._waits = {}
        self._targets = []
        self._task = None


    def __enter__(self):
        self.start()
    def __exit__(self, type, value, traceback):
        self.stop()

    async def __aenter__(self):
        self.start()

    async def __aexit__(self, type, value, traceback):
        await self.astop()

    def start(self):
        '''
        Spawn the auto-stepping task.
        '''
        if self._task is None:
            self._task = aio.ensure_future(self._process())
        return self._task

    def stop(self):
        '''
        Kill the auto-stepping task.
        '''
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def astop(self):
        if self._task is not None:
            self._task.cancel()
            await aio.wait([self._task])

    async def step(self, dt=0):
        '''
        Step through queue'd events scheduled to be released within the next
        dt seconds.
        '''
        # fire any instants (like ensure_future) before 'waiting'
        # this fixes the case where a spawned function adds a sleep
        await self.fastsleep()
        # print('gt:',self.now,self._targets)
        if len(self._targets) == 0:
            # no sleeps, just advance the time
            self._current += dt
            await self.fastsleep()
        else:
            # sort targets so we we get the ones to process in front
            self._targets.sort()

            # keep stepping till we hit an end time
            step_to = self.now + dt if dt else self._targets[0]
            while self.now < step_to:
                # step a specific amount of time or to the first target
                new = min(step_to, self._targets[0])
                self._current = new
                # print('gt2:',self.now,self._targets)
                for target in list(self._targets):
                    if target <= new:
                        for event in self._waits[target]:
                            event.set() # does not switch
                    else:
                        break

                # switch to run released events
                await self.fastsleep()

    async def _process(self):
        while self._task is not None:
            # auto-step to next sleep
            await self.step()
            # give up control
            await self.fastsleep()

    async def fastsleep(self, dt=0):
        '''
        Add a new event scheduled to be released when .now advances dt seconds,
        then .wait() for it to be released.
        '''
        if dt <= 0:
            await self._real_sleep(0)
        else:
            e = aio.Event()
            target = self.now + dt
            self._waits.setdefault(target, []).append(e)
            self._targets.append(target)
            try:
                await e.wait()
            finally:
                self._waits[target].remove(e)
                self._targets.remove(target)


@pytest.fixture
def fastsleep(request, monkeypatch):
    '''
    Fixture for using FastSleep in py.test
    '''
    return FastSleep(monkeypatch)

@pytest.fixture
def fancysleep(monkeypatch):
    '''
    Fixture for using FancySleep in py.test
    '''
    return FancySleep(monkeypatch)
