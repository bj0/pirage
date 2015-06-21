# manage garage state

import time
from asyncio import coroutine, async, sleep

class Garage:
    '''
    Manage the state of the garage.
    '''

    def __init__(self, toggle_function):
        self.door_open = False
        self.motion = False
        self.last_door_open = None
        self.last_motion = None
        self.locked = False

        self.task = None
        self.close_task = None
        self.notify_task = None

        self.motion_delay = 5*60 # 5 min
        self.notify_delay = 6*60 # 6 min
        self.close_delay = 15*60 # 15 min
        self.close_warning = 5*60 # 5 min

        self._toggle = toggle_function

    def update(self, state):
        # check door
        if state.mag != self.door_open:
            if state.mag:
                # door is now open!
                self.notify("door open!")
                if self.close_task is not None:
                    self.close_task.cancel()
                self.close_task = async(self.close_after(self.close_delay))

                if self.notify_task is not None:
                    self.notify_task.cancel()
                self.notify_task = async(self.notify_after(
                    "Garage is still open after {mag_open} minutes!",
                    self.notify_delay))

            else:
                # door is now closed!
                self.notify("door closed!")

        # check pir
        if state.pir and not self.motion:
            # motion!
            self.notify("motion!")

        # save state
        self.motion = state.pir
        self.door_open = state.mag
        if self.motion:
            self.last_motion = time.time()
        if self.door_open:
            self.last_door_open = time.time()

    def is_someone_home(self):
        pass #TODO

    @coroutine
    def close_after(self, seconds):
        '''
        Close the garage door after specified number of seconds.
        The close can be delayed by movement (last_pir is checked before close)
        '''
        if seconds <= self.close_warning:
            if seconds < 60:
                self.notify("closing garage in {} seconds!", seconds)
            else:
                self.notify("closing garage in {} minutes!".format(seconds/60))
        else:
            # warn 5 minutes before close
            yield from sleep(seconds - self.close_warning)
            seconds -= self.close_warning
            if seconds < 60:
                self.notify("closing garage in {} seconds!", seconds)
            else:
                self.notify("closing garage in {} minutes!".format(seconds/60))

        # wait for time to elapse
        yield from sleep(seconds)

        # if there was movement, we delay
        now = time.time()
        while (now - self.last_motion) < self.motion_delay:
            self.notify("garage close delayed by movement!")
            yield from sleep(now - self.last_motion + 5)
            now = time.time()

        # clear task since it can no longer be canceled
        self.close_task = None

        # no longer delayed, close the door!
        self.toggle_door()

    @coroutine
    def notify_after(self, seconds, message, repeat=True):
        '''
        Send a notification after specified number of seconds.
        If @repeat is True, the notification will be sent every @seconds seconds.
        '''
        yield from sleep(seconds)
        self.notify(message)

        while repeat:
            yield from sleep(seconds)
            self.notify(message)

        self.notify_task = None

    def notify(self, message):
        message = message.format(
            open="Open" if self.door_open else "Closed",
            mag_open = (time.time()-self.last_door_open)/60 )
        print(message)
        #TODO email?

    def toggle_door(self):
        self._toggle()
