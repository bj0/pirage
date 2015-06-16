# -*- coding: utf-8 -*-
'''
hardware.py

Module for interfacing with Raspberry Pi Hardware.

Monitor:
    Monitor pins on the rpi for changes from a PIR sensors and a magnetic switch sensor.

According to the spec, the PIR sensor's pin is HIGH when there is movement, else low.

The magnetic switch's requires a pull-up resister (internal), and is closed when the magnet is near the switch.

They can be checked like so::

    import RPi.GPIO as io
    ...

    io.setup(pir_pin, io.IN)
    io.setup(door_pin, io.IN, pull_up_down=io.PUD_UP)

    if io.input(pir_pin):
        print("PIR ACTIVE")
    if io.input(mag_pin):
        print("MAG ACTIVE")

author:: Brian Parma <execrable@gmail.com>
'''

from asyncio import coroutine, async, sleep
import RPi.GPIO as io

_pir_pin = #TODO
_mag_pin = #TODO

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

class Monitor:
    '''
    Monitor the rpi sensors and report changes.

    *This should be a singleton*

    Register callbacks to receive notifications::

        m = Monitor()
        m.register(callback)

    Callbacks receive a dict of sensor data in the following format:

        {
            'mag':True      # mag switch is open
            'pir':False     # pir sensor is inactive
        }

    '''
    def __init__(self):
        self._callbacks = []
        self.running = None
        self._current = None

        # set number scheme
        io.setmode(io.BCM)

        # init pins
        io.setup(_pir_pin, io.IN)
        io.setup(_mag_pin, io.IN, pull_up_down=io.PUD_UP)

    def start(self):
        '''
        Start monitoring sensors.
        '''
        if self.running is None:
            self.running = async(self._run())

    def stop(self):
        '''
        Stop monitoring sensors.
        '''
        if self.running is not None:
            self.running.cancel()
            self.running = None

    #@threaded
    @coroutine
    def _run(self):
        while self.running:
            # read current sensors
            state = self._read_sensors()
            if self._current is None or self._current.mag != state.mag or \
                self._current.pir != state.pir:
                if self._current is None:
                    self._current = AttrDict()
                # something changed
                self._current.pir = state.pir
                self._current.mag = state.mag
                self.publish(dict(self._current))

            # pause
            yield from sleep(1)

        # monitoring stopped
        self._current = None

    def register(self, callback):
        '''
        Register a callback to be called when a sensor changes.
        '''
        self._callbacks.append(callback)

    def unregister(self, callback):
        '''
        Unregister a previously registered callback.
        '''
        self._callbacks.remove(callback)

    def publish(self, *args, **kwargs):
        '''
        Call registered callbacks with specified args and kwargs.
        '''
        for cb in self._callbacks:
            cb(*args, **kwargs)

    def _read_sensors(self):
        #TODO
