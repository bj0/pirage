# -*- coding: utf-8 -*-
'''
hardware.py

Module for interfacing with Raspberry Pi Hardware.

Monitor:
    Monitor pins on the rpi for changes from a PIR sensors and a magnetic switch sensor.

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
'''

# from asyncio import coroutine, async, sleep, get_event_loop
from __future__ import print_function
from gevent import spawn, sleep
try:
    import RPi.GPIO as io
except:
    # mock GPIO for running on desktop
    print('no RPi.GPIO, mocking')
    from mock import MagicMock
    from itertools import cycle
    io = MagicMock()
    io.HIGH = 1
    io.LOW = 0
    io.OUT = 0
    io.IN = 1
    io.input = MagicMock()
    io.input.side_effect = cycle((io.HIGH, io.LOW, io.HIGH, io.LOW, io.LOW))
    io.output = MagicMock()
    io.output.side_effect = lambda *x: print('out:',*x)

from .util import AttrDict

_pir_pin = 18
_mag_pin = 23
_relay_pin = 24

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
        self._current = AttrDict(mag=None, pir=None)
        self._run_task = None
        self._ignore_pir = False

        self.read_interval = 2 # 2 second

        # set number scheme
        io.setmode(io.BCM)

        # init pins
        if not self.ignore_pir:
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

    def start(self):
        '''
        Start monitoring sensors.
        '''
        if not self.running:
            self._run_task = spawn(self.run)

        # return the task so it can be watched
        return self._run_task

    def stop(self):
        '''
        Stop monitoring sensors.
        '''
        if self.running is not None:
            # self.running.cancel()
            self.running = False
            self._run_task.kill()
            self._run_task = None

    #@threaded
    # @coroutine
    def run(self):
        '''
        Read the sensors every interval and publish any changes.  Runs until canceled.

        This is a @coroutine
        '''

        self.running = True
        while self.running:
            # read current sensors
            state = self._read_sensors()
            if self._current.mag != state.mag or \
                self._current.pir != state.pir:

                # something changed
                self._current.pir = state.pir
                self._current.mag = state.mag
                self.publish(self._current)

            # pause
            # yield from sleep(self.read_interval)
            sleep(self.read_interval)

        # monitoring stopped
        self._current = AttrDict(mag=None, pir=None)

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

    # @coroutine
    def toggle_relay(self):
        '''
        Flip the relay on for 0.5s to simulate a "button press"
        '''
        io.output(_relay_pin, io.LOW)
        # yield return sleep(0.5)
        sleep(0.5)
        io.output(_relay_pin, io.HIGH)

    def _read_sensors(self):
        state = AttrDict()
        state.pir = io.input(_pir_pin) if not self.ignore_pir else 0
        state.mag = io.input(_mag_pin)

        return state

if __name__ == '__main__':
    # run stand alone to interactively test the hardware interaction
    # options:
    # - gevent with patched raw_input/input (no py3)
    # - eventlet with aioeventlet (works with py3 and asyncio), what about input?
    # - pure asyncio? what about input?
    from gevent import monkey, spawn
    monkey.patch_sys()

    m = Monitor()

    # this accepts input without blocking gevent
    def prompt(msg):
        print(msg)
        while True:
            cmd = raw_input().lower()
            if cmd == 'q':
                break
            elif cmd == 'r':
                m.toggle_relay()
            else:
                print('unknown cmd')

    # print on input change
    m.register(lambda *x: print('pub:',*x))
    m.start()
    gt = spawn(prompt("enter q to quit, r to relay"))
    gt.join()
    m.stop()
