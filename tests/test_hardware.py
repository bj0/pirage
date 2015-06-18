from __future__ import absolute_import

from mock import MagicMock
import pytest

import gevent
from gevent import spawn, sleep

from pirage.hardware import Monitor

@pytest.fixture
def fastsleep(monkeypatch):
    old_sleep = gevent.sleep
    def patch(module):
        monkeypatch.setattr(module, lambda *x: old_sleep(0))

    patch('gevent.sleep')
    return patch

@pytest.fixture(autouse=True)
def gpio(monkeypatch):
    io = MagicMock()
    io.HIGH = 1
    io.LOW = 0

    monkeypatch.setattr('pirage.hardware.io', io)

    return io

def test_run_fires_callback_on_start():
    mm = MagicMock()
    m = Monitor()
    m.register(mm.callback)

    m.start()
    sleep(0) # let greenlet run once
    m.stop()
    assert mm.callback.called
    assert len(mm.callback.mock_calls) == 1

def test_run_fires_callback_on_change(fastsleep, gpio):
    from itertools import cycle
    fastsleep('pirage.hardware.sleep')

    # no changes on input
    gpio.input.side_effect = cycle((gpio.HIGH,gpio.LOW))

    mm = MagicMock()
    m = Monitor()
    m.register(mm.callback)

    m.start()
    gevent.sleep() # let greenlet run once
    gevent.sleep() # let greenlet run once
    gevent.sleep() # let greenlet run once
    gevent.sleep() # let greenlet run once

    assert len(mm.callback.mock_calls) == 1 # only called once

    # make changes (after first call)
    gpio.input.side_effect = cycle((gpio.HIGH,gpio.LOW,gpio.LOW))

    gevent.sleep() # let greenlet run once

    # no extra calls
    assert len(mm.callback.mock_calls) == 1

    gevent.sleep() # let greenlet run once
    gevent.sleep() # let greenlet run once
    gevent.sleep() # let greenlet run once

    # 3 new calls
    assert len(mm.callback.mock_calls) == 4

def test_relay_starts_low(gpio):
    from pirage import hardware as hw
    m = Monitor()
    gpio.output.assert_called_once_with(hw._relay_pin, gpio.LOW)

def test_toggle_relay(fastsleep, gpio):
    fastsleep('pirage.hardware.sleep')
    from pirage import hardware as hw

    m = Monitor()
    gpio.output.reset_mock()
    # put it in a greenlet so we can step it
    spawn(m.toggle_relay)
    gevent.sleep() # step to pause

    gpio.output.assert_called_once_with(hw._relay_pin, gpio.HIGH)
    gevent.sleep() # step
    gpio.output.assert_called_with(hw._relay_pin, gpio.LOW)
