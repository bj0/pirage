from unittest.mock import MagicMock, call

import pytest

# for assert_does_not_have_calls
# noinspection PyUnresolvedReferences
import pirage.tests
from pirage.hardware import Hardware, Sensors


@pytest.fixture(autouse=True)
def gpio(monkeypatch):
    io = MagicMock()
    io.HIGH = 1
    io.LOW = 0
    io.OUT = 0
    io.IN = 1

    monkeypatch.setattr('pirage.hardware.io', io)

    return io


def test_reading_sensors(gpio):
    from itertools import cycle

    # mag switch toggles
    gpio.input.side_effect = cycle((gpio.LOW, gpio.HIGH))

    m = Hardware()

    m.ignore_pir = True  # disable pir input

    assert m.read_sensors() == Sensors(**{'pir': gpio.LOW, 'mag': gpio.LOW})
    assert m.read_sensors() == Sensors(**{'pir': gpio.LOW, 'mag': gpio.HIGH})
    assert m.read_sensors() == Sensors(**{'pir': gpio.LOW, 'mag': gpio.LOW})


async def test_no_pir(gpio):
    """
    make sure we ignore pir sensor if disabled
    """
    from pirage import hardware as hw
    from itertools import cycle

    # we only read door pin
    gpio.input.side_effect = cycle((gpio.LOW,))

    m = Hardware()
    m.ignore_pir = True  # disable pir input

    m.read_sensors()
    m.read_sensors()
    m.read_sensors()
    m.read_sensors()
    gpio.input.assert_does_not_have_calls([call(hw._relay_pin)])


# def test_relay_starts_high(gpio):
#     from pirage import hardware as hw
#     m = Hardware()
#     # gpio.output.assert_called_once_with(hw._relay_pin, gpio.HIGH)
#     gpio.setup.assert_called_with(hw._relay_pin, gpio.OUT, initial=gpio.HIGH)


async def test_toggle_relay(gpio):
    from pirage import hardware as hw

    m = Hardware()
    gpio.output.reset_mock()
    await m.toggle_relay()

    gpio.output.assert_has_calls([call(hw._relay_pin, gpio.LOW), call(hw._relay_pin, gpio.HIGH)])
