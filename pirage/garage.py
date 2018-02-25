# manage garage state

import asyncio as aio
import logging
import os
import time
from pathlib import Path

from .util import shelf, AttrDict, create_task

logger = logging.getLogger(__name__)


class Garage:
    """
    Manage the state of the garage.
    """

    def __init__(self, toggle_function):
        self.door_open = False
        self.motion = False
        self.last_door_change = None
        self.last_motion = None
        self._locked = False

        self.task = None
        self.close_task = None
        self.notify_task = None

        self.motion_delay = 5 * 60  # 5 min
        self.notify_delay = 6 * 60  # 6 min
        self.close_delay = 15 * 60  # 15 min
        self.close_warning = 5 * 60  # 5 min

        self._toggle = toggle_function

    def lock(self, locked=True):
        self._locked = locked
        if locked:
            # stop any auto-close
            if self.close_task is not None:
                self.close_task.cancel()
                self.close_task = None
        elif self.close_task is None and self.door_open:
            # start up a close
            self.notify('starting up auto-close from unlock')
            self.close_task = create_task(self.close_after(self.close_delay))

    def save(self):
        """
        Save last sensor change times to disk.
        """
        path = Path(Path.home(), ".pirage/")
        if not path.exists():
            path.mkdir()
        with shelf(str(path / "data.db")) as s:
            s['state'] = {
                'last_door_change': self.last_door_change,
                'last_motion': self.last_motion,
            }

    def load(self):
        """
        Load last sensor change times to disk.
        """
        if not os.path.exists('/var/lib/pirage'):
            return
        with shelf('/var/lib/pirage/data.db') as s:
            d = s.get('state', {})
            self.last_door_change = d.get('last_door_change', None)
            self.last_motion = d.get('last_motion', None)

    def update(self, state):
        # check door
        # state.mag = not state.mag  # since the door switch is "closed" when the door is "open"
        if state.mag != self.door_open:
            self.last_door_change = time.time()
            if self.notify_task is not None:
                self.notify_task.cancel()
                self.notify_task = None
            if state.mag:
                # door is now open!
                self.notify("door open!")
                if self.close_task is not None:
                    self.close_task.cancel()
                    self.close_task = None
                if not self.locked:
                    self.close_task = aio.ensure_future(self.close_after(self.close_delay))

                self.notify_task = aio.ensure_future(self.notify_after(
                    "Garage is still open after {mag_open} minutes!",
                    self.notify_delay))

            else:
                # door is now closed!
                self.notify("door closed!")
                # clear auto-close task
                if self.close_task is not None:
                    self.close_task.cancel()
                    self.close_task = None

        # check pir
        if state.pir and not self.motion:
            # motion!
            self.notify("motion!")

        # save state
        self.motion = state.pir
        self.door_open = state.mag
        if self.motion:
            self.last_motion = time.time()

    def is_someone_home(self):
        pass  # TODO

    async def close_after(self, seconds):
        """
        Close the garage door after specified number of seconds.
        The close can be delayed by movement (last_pir is checked before close)
        """
        if seconds <= self.close_warning:
            if seconds < 60:
                self.notify("closing garage in {} seconds!".format(seconds))
            else:
                self.notify("closing garage in {} minutes!".format(seconds / 60))
        else:
            # warn 5 minutes before close
            await aio.sleep(seconds - self.close_warning)
            seconds = self.close_warning
            if seconds < 60:
                self.notify("closing garage in {} seconds!".format(seconds))
            else:
                self.notify("closing garage in {} minutes!".format(seconds / 60))

        # wait for time to elapse
        await aio.sleep(seconds)

        # if there was movement, we delay
        now = time.time()
        last_motion = self.last_motion or (now - self.motion_delay - 1)
        while (now - last_motion) < self.motion_delay:
            self.notify("garage close delayed by movement!")
            await aio.sleep(self.motion_delay - (now - last_motion))
            now = time.time()
            last_motion = self.last_motion

        # clear task since it can no longer be canceled
        # self.close_task = None

        # no longer delayed, close the door (only if open)!
        if self.door_open:
            self.toggle_door()
        else:
            self.notify("got auto-close on closed door!")

    async def notify_after(self, message, seconds, repeat=True):
        """
        Send a notification after specified number of seconds.
        If @repeat is True, the notification will be sent every @seconds seconds.
        """
        await aio.sleep(seconds)
        self.notify(message)

        while repeat:
            await aio.sleep(seconds)
            self.notify(message)

    def notify(self, message):
        if self.last_door_change is not None:
            mag_open = (time.time() - self.last_door_change) / 60
        else:
            mag_open = 0
        message = message.format(
            open="Open" if self.door_open else "Closed",
            mag_open=mag_open)
        print(message)
        logger.info(message)
        # TODO email? dweet?

    def toggle_door(self):
        logger.info('toggling door')
        self._toggle()

    @property
    def locked(self):
        return self._locked

    @locked.setter
    def locked(self, value):
        self.lock(value)

    @property
    def data(self):
        """
        Package up current data in a usable form.
        """
        now = time.time()
        last_pir = int(now - (self.last_motion or 0))
        last_mag = int(now - (self.last_door_change or 0))
        if last_pir > 60:
            last_pir_str = '{} min'.format(last_pir // 60)
        else:
            last_pir_str = '{} sec'.format(last_pir)

        if last_mag > 60:
            last_mag_str = '{} min'.format(last_mag // 60)
        else:
            last_mag_str = '{} sec'.format(last_mag)

        data = AttrDict(
            now=now,
            last_pir=last_pir,
            last_mag=last_mag,
            last_pir_str=last_pir_str,
            last_mag_str=last_mag_str,
            pir=self.motion, mag=self.door_open
        )

        return data
