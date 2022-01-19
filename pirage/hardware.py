# -*- coding: utf-8 -*-
"""
hardware.py

Module for interfacing with Raspberry Pi Hardware.

Hardware:
    Read pins on the rpi for  a PIR sensors and a magnetic switch sensor.

According to the spec, the PIR sensor's pin is HIGH when there is movement, else low.
 * HIGH when there is movement

The magnetic switch's requires a pull-up resister (internal), and is closed when the magnet is near the switch.
 * HIGH when magnet is not by switch (OPEN)

They can be checked like so::

    import RPi.GPIO as io
    ...

    io.setup(pir_pin, io.IN)
    io.setup(door_pin, io.IN, pull_up_down=io.PUD_UP)

    if io.input(pir_pin):
        print("MOVEMENT DETECTED!")
    if io.input(mag_pin):
        print("MAG OPEN!")

GPIO pins used are:
    18 - PIR
    23 - mag
    24 - relay

The relay module needs to be HIGH at startup or it will activate (it activates when LOW)
 * HIGH -> LOW to activate

author:: Brian Parma <execrable@gmail.com>
"""

import logging
from dataclasses import dataclass

import trio
from clii import App

logger = logging.getLogger(__name__)

cli = App()

try:
    import RPi.GPIO as io

    _fake = False
except (ImportError, RuntimeError):
    # mock GPIO for running on desktop
    logger.warning('no RPi.GPIO, mocking')
    from unittest.mock import MagicMock
    from itertools import cycle

    _fake = True
    io = MagicMock()
    io.HIGH = 1
    io.LOW = 0
    io.OUT = 0
    io.IN = 1
    io.input = MagicMock()
    io.input.side_effect = cycle((io.HIGH, io.LOW, io.HIGH, io.LOW, io.LOW))
    io.output = MagicMock()
    # print on write
    io.output.side_effect = lambda *x: print('out:', *x)

_pir_pin = 18
_mag_pin = 23
_relay_pin = 24


@dataclass
class Sensors:
    pir: bool
    mag: bool


class Hardware:
    """
    access to the rpi sensors.

    *this should be a singleton*
    """

    def __init__(self):
        self._ignore_pir = False

        # set number scheme
        io.setmode(io.BCM)

        # init pins
        # if not self.ignore_pir:
        io.setup(_pir_pin, io.IN)
        io.setup(_mag_pin, io.IN, pull_up_down=io.PUD_UP)
        io.setup(_relay_pin, io.OUT, initial=io.HIGH)
        # make sure relay doesn't click when we start
        # io.output(_relay_pin, io.HIGH)

    @property
    def ignore_pir(self):
        return self._ignore_pir

    @ignore_pir.setter
    def ignore_pir(self, value):
        self._ignore_pir = value

    def read_sensors(self) -> Sensors:
        return Sensors(
            pir=io.input(_pir_pin) if not self.ignore_pir else 0,
            mag=io.input(_mag_pin))

    @classmethod
    async def toggle_relay(cls):
        """
        Flip the relay on for 0.5s to simulate a "button press"

        This is a coroutine.
        """
        io.output(_relay_pin, io.LOW)
        await trio.sleep(0.5)
        io.output(_relay_pin, io.HIGH)


@cli.cmd
def read_temp():
    with open('/sys/class/thermal/thermal_zone0/temp', 'rt') as f:
        data = f.readline()
        if data:
            return float(data) / 1e3


@cli.main
async def main():
    import sys
    m = Hardware()

    async with trio.lowlevel.FdStream(sys.stdin.fileno()) as stdin:
        async for line in stdin:
            if line.startswith(b'r'):
                await m.toggle_relay()
            elif line.startswith(b'q'):
                break


if __name__ == '__main__':
    # run stand alone to interactively test the hardware interaction
    trio.run(cli.run)
