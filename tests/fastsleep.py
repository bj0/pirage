from __future__ import absolute_import

import pytest

import gevent
import gevent.event

class FastSleep(object):
    def __init__(self, monkeypatch):
        self._monkey = monkeypatch
        self._real_sleep = gevent.sleep
        self._current = 0

        self.patch('gevent.sleep')

    @property
    def now(self):
        return self._current

    def patch(self, module):
        self._monkey.setattr(module, self.fastsleep)

    def fastsleep(self, dt=0):
        self._current += dt
        self._real_sleep(0)


class FancySleep(FastSleep):
    """docstring for FastSleep"""
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
        if self._gt is None:
            self._gt = gevent.spawn(self._process)

    def stop(self):
        if self._gt is not None:
            self._gt.kill()
            self._gt = None

    def step(self, dt=0):
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
    return FastSleep(monkeypatch)

@pytest.fixture
def fancysleep(monkeypatch):
    return FancySleep(monkeypatch)
