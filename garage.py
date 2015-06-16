# manage garage state

import time
from asyncio import coroutine, async, sleep

class Garage:
    '''
    A class to hold and manage the state of the garage.
    '''

    def __init__(self):
        self.door_open = False
        self.pir = False
        self.last_door = None
        self.last_pir = None
        self.locked = False

        self.task = None
        self.close_task = None
        self.notify_task = None

        self.motion_delay = 5*60 # 5 min
        self.close_delay = 15*60 # 15 min
        self.close_warning = 5*60 # 5 min

    def update(self, state):
        # check door
        if state.mag != self.door_open:
            if state.mag:
                # door is now open!
                notify("door open!")
                if self.close_task is not None:
                    self.close_task.cancel()
                self.close_task = async(self.close_after(self.close_delay))

                if self.notify_task is not None:
                    self.notify_task.cancel()
                self.notify_task = async(self.notify_after("Garage is still open after {mag_open} minutes!", 6*60))

            else:
                # door is now closed!
                notify("door closed!")

        # check pir
        if state.pir and not self.pir:
            # motion!
            notify("motion!")

        # save state
        self.pir = state.pir
        self.door_open = state.mag
        if self.pir:
            self.last_pir = time.time()
        if self.door_open:
            self.last_mag = time.time()

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
                notify("closing garage in {} seconds!", seconds)
            else:
                notify("closing garage in {} minutes!".format(seconds/60))
        else:
            # warn 5 minutes before close
            yield from sleep(seconds - self.close_warning)
            seconds -= self.close_warning
            if seconds < 60:
                notify("closing garage in {} seconds!", seconds)
            else:
                notify("closing garage in {} minutes!".format(seconds/60))

        # wait for time to elapse
        yield from sleep(seconds)

        # if there was movement, we delay
        now = time.time()
        while (now - self.last_pir) < self.motion_delay:
            notify("garage close delayed by movement!")
            yield from sleep(now - self.last_pir + 5)
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
        notify(message)

        while repeat:
            yield from sleep(seconds)
            notify(message)

        self.notify_task = None

    # def start(self):
    #     '''start managing the garage'''
    #     if self.task is None:
    #         print('starting management task')
    #         self.task = async(self._run())
    #
    # def stop(self):
    #     '''stop managing the garage'''
    #     if self.task is not None:
    #         print('stopping management task')
    #         self.task.cancel()
    #         self.task = None
    #
    # @coroutine
    # def _run(self):
    #     while True:
    #         # TODO notifies
    #         if self.notify_after is not None and self.notify_after < time.time():
    #             self.notify("Dat NOTIFY!")
    #             # repeat notify every 5 minute
    #             self.notify_after = time.time() + 5*60
    #
    #         if self.door_open:
    #             # if there's currently motion, wait a few seconds and check again
    #             if self.pir:
    #                 yield from sleep(10)
    #                 continue
    #             # close the door after a certain time if it's not locked open
    #             # and there is no motion
    #             if not self.locked and \
    #                 (self.close_after is not None and self.close_after < time.time()):
    #                 self.toggle_door()
    #
    #         # check again in a minute
    #         yield from sleep(60)

    def notify(self, message):
        message = message.format(
            open="Open" if self.door_open else "Closed",
            mag_open = (time.time()-self.last_mag)/60 )
        print(message)
        #TODO email?

    def toggle_door(self):
        pass
