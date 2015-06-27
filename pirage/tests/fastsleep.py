from __future__ import absolute_import

import pytest

import gevent
import gevent.event

class FastSleep(object):
    '''
    FastSleep patches gevent.sleep so that every gevent.sleep(N) becomes
    gevent.sleep(0).  This effectively changes it to a no-wait context switch.
    The seconds passed to .sleep(N) are summed up and available from
    FastSleep.now.

    If sleep is imported with from gevent import sleep, FastSleep can be used
    to patch it with::

    fastsleep.patch('module.sleep')
    '''
    def __init__(self, monkeypatch):
        self._monkey = monkeypatch
        self._real_sleep = gevent.sleep
        self._current = 0

        self.patch('gevent.sleep')

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

    def fastsleep(self, dt=0):
        '''
        Add dt to running sum and .sleep(0) for a context switch.  This is the function
        patched into gevent.sleep.
        '''
        self._current += dt
        self._real_sleep(0)


class FancySleep(FastSleep):
    """
    FancySleep patches gevent.sleep like FastSleep, but instead of simply
    replacing it with a context switch, FancySleep uses gevent.event.Event
    to explicitly control the order of greenthreads resuming from .sleep.

    This allows FancySleep to control the execution order and "time" that
    greenthreads are resumed from .sleep.  The "time", tracked by .now, can be
    advanced manually with::

    fancysleep.step(N)

    or automatically.  Stepping advances to each
    Event added by .sleep until it reaches the .step time or runs out of Events.

    **WARNING:** Since FancySleep uses gevent.event.Event to effectively lock
    a greenthread until itself releases it, simply calling gevent.sleep in the
    "main" greenthread will deadlock (actually gevent will throw an exception).
    To prevent his from happening there are two options:

     1) Make sure any code that uses gevent.sleep is executed in a separate
     greenthread.  This can be done by wrapping code in gevent.spawn.  The main
     greenthread can then use .step to manually advance, unlocking the sleeping
     greenthreads.

     2) *RECOMMENDED:* Enable automatic stepping by calling .start on fancysleep
     before executing any code that uses gevent.sleep.  This will spawn a
     greenthread that automatically steps to the next Event whenever the main
     greenthread switches its context.  This allows manually stepping through
     "time" using either .step OR gevent.sleep in the main greenthread.  This
     auto-stepping greenthread will run until explicitly stopped with .stop.

    To advance automatically, start FancySleep before calling code that uses
    gevent.sleep, and stop it after::

    fancysleep.start()
    gevent.sleep(100)
    function_that_sleeps()
    fancysleep.stop()

    Alternatively, FancySleep can be used as a context manager to automatically
    start and stop it's automatic stepping::

    with fancysleep:
        gevent.sleep(100)
        function_that_sleeps()

    """
    def __init__(self, monkeypatch):
        super(FancySleep, self).__init__(monkeypatch)
        self._waits = {}
        self._targets = []
        self._gt = None


    def __enter__(self):
        self.start()
    def __exit__(self, type, value, traceback):
        self.stop()

    def start(self):
        '''
        Spawn the auto-stepping greenthread.
        '''
        if self._gt is None:
            self._gt = gevent.spawn(self._process)

    def stop(self):
        '''
        Kill the auto-stepping greenthread.
        '''
        if self._gt is not None:
            self._gt.kill()
            self._gt = None

    def step(self, dt=0):
        '''
        Step through queue'd events scheduled to be released within the next
        dt seconds.
        '''
        # fire any instants (like spawn) before 'waiting'
        # this fixes the case where a spawned function adds a sleep
        self.fastsleep()
        # print('gt:',self.now,self._targets)
        if len(self._targets) == 0:
            # no sleeps, just advance the time
            self._current += dt
            self.fastsleep()
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
                self.fastsleep()

    def _process(self):
        while self._gt is not None:
            # auto-step to next sleep
            self.step()
            # give up control
            self.fastsleep()

    def fastsleep(self, dt=0):
        '''
        Add a new event scheduled to be released when .now advances dt seconds,
        then .wait() for it to be released.
        '''
        if dt <= 0:
            self._real_sleep(0)
        else:
            e = gevent.event.Event()
            target = self.now + dt
            self._waits.setdefault(target, []).append(e)
            self._targets.append(target)
            try:
                e.wait()
            finally:
                self._waits[target].remove(e)
                self._targets.remove(target)


@pytest.fixture
def fastsleep(monkeypatch):
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
