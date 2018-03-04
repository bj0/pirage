import asyncio as aio
from unittest.mock import MagicMock

import pytest

from pirage.hardware import Monitor


@pytest.fixture(autouse=True)
def gpio(monkeypatch):
    io = MagicMock()
    io.HIGH = 1
    io.LOW = 0
    io.OUT = 0
    io.IN = 1

    monkeypatch.setattr('pirage.hardware.io', io)

    return io


@pytest.mark.asyncio
async def test_modifying_update_result_doesnt_break(fastsleep, gpio):
    from itertools import cycle
    # fastsleep.patch('pirage.hardware.sleep')

    # mag switch toggles
    gpio.input.side_effect = cycle((gpio.LOW, gpio.HIGH))

    mm = MagicMock()
    m = Monitor()

    def mod(r):
        r.mag = not r.mag
        r.x = 5

    mm.callback.side_effect = mod
    m.register(mm.callback)
    m.start()
    await aio.sleep()  # no change L / H
    m.ignore_pir = True  # disable pir input
    await aio.sleep()  # change L / L
    # hack, since mock doesn't keep immutable call args
    assert m._current == {'pir': gpio.LOW, 'mag': gpio.LOW}
    await aio.sleep()  # change L / H
    assert m._current == {'pir': gpio.LOW, 'mag': gpio.HIGH}
    await aio.sleep()  # change L / L
    assert m._current == {'pir': gpio.LOW, 'mag': gpio.LOW}
    await m.stop()

    assert len(mm.callback.mock_calls) == 4


@pytest.mark.asyncio
async def test_no_pir(fastsleep, gpio):
    """
    make sure we ignore pir sensor if disabled
    """
    from pirage import hardware as hw
    from itertools import cycle
    # fastsleep.patch('pirage.hardware.sleep')

    # we only read door pin
    gpio.input.side_effect = cycle((gpio.LOW,))

    mm = MagicMock()
    m = Monitor()
    m.ignore_pir = True  # disable pir input
    m.register(mm.callback)

    m.start()
    await aio.sleep()  # let greenlet run once
    gpio.input.assert_called_with(hw._mag_pin)
    await aio.sleep()  # let greenlet run once
    gpio.input.assert_called_with(hw._mag_pin)
    await aio.sleep()  # let greenlet run once
    gpio.input.assert_called_with(hw._mag_pin)
    await aio.sleep()  # let greenlet run once
    gpio.input.assert_called_with(hw._mag_pin)
    await m.stop()

    assert len(mm.callback.mock_calls) == 1  # only called once
    assert len(gpio.input.mock_calls) == 4  # only mag is checked


@pytest.mark.asyncio
async def test_no_pir_door_still_works(fastsleep, gpio):
    from itertools import cycle
    # fastsleep.patch('pirage.hardware.sleep')

    # mag swithc toggles
    gpio.input.side_effect = cycle((gpio.LOW, gpio.HIGH))

    mm = MagicMock()
    m = Monitor()
    m.register(mm.callback)
    m.start()
    await aio.sleep()  # no change L / H
    m.ignore_pir = True  # disable pir input
    await aio.sleep()  # change L / L
    mm.callback.assert_called_with({'pir': gpio.LOW, 'mag': gpio.LOW})
    await aio.sleep()  # change L / H
    mm.callback.assert_called_with({'pir': gpio.LOW, 'mag': gpio.HIGH})
    await aio.sleep()  # change L / L
    mm.callback.assert_called_with({'pir': gpio.LOW, 'mag': gpio.LOW})
    await m.stop()

    assert len(mm.callback.mock_calls) == 4


@pytest.mark.asyncio
async def test_run_fires_callback_on_start():
    mm = MagicMock()
    m = Monitor()
    m.register(mm.callback)

    m.start()
    await aio.sleep(0)  # let greenlet run once
    await m.stop()
    assert mm.callback.called
    assert len(mm.callback.mock_calls) == 1


@pytest.mark.asyncio
async def test_run_fires_callback_on_change(fastsleep, gpio):
    from itertools import cycle
    # fastsleep.patch('pirage.hardware.sleep')

    # no changes on input
    gpio.input.side_effect = cycle((gpio.HIGH, gpio.LOW))

    mm = MagicMock()
    m = Monitor()
    m.register(mm.callback)

    m.start()
    await aio.sleep()  # let greenlet run once
    await aio.sleep()  # let greenlet run once
    await aio.sleep()  # let greenlet run once
    await aio.sleep()  # let greenlet run once

    assert len(mm.callback.mock_calls) == 1  # only called once

    # make changes (after first call)
    gpio.input.side_effect = cycle((gpio.HIGH, gpio.LOW, gpio.LOW))

    await aio.sleep()  # let greenlet run once

    # no extra calls
    assert len(mm.callback.mock_calls) == 1

    await aio.sleep()  # let greenlet run once
    await aio.sleep()  # let greenlet run once
    await aio.sleep()  # let greenlet run once

    # 3 new calls
    assert len(mm.callback.mock_calls) == 4

    await m.stop()


def test_relay_starts_high(gpio):
    from pirage import hardware as hw
    m = Monitor()
    # gpio.output.assert_called_once_with(hw._relay_pin, gpio.HIGH)
    gpio.setup.assert_called_with(hw._relay_pin, gpio.OUT, initial=gpio.HIGH)


@pytest.mark.asyncio
async def test_toggle_relay(fastsleep, gpio):
    # fastsleep.patch('pirage.hardware.sleep')
    from pirage import hardware as hw

    m = Monitor()
    gpio.output.reset_mock()
    # put it in a greenlet so we can step it
    aio.ensure_future(m.toggle_relay())
    await aio.sleep()  # step to pause

    gpio.output.assert_called_once_with(hw._relay_pin, gpio.LOW)
    await aio.sleep()  # step
    gpio.output.assert_called_with(hw._relay_pin, gpio.HIGH)
