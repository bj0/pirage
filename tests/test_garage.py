from __future__ import absolute_import

import pytest
import gevent
import mock

from .hardware import AttrDict
from fastsleep import fastsleep, fancysleep

def test_garage_autoclose(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    monkeypatch('time.time', lambda: fancysleep.now)

    g = Garage(toggle)
    # initial setup
    g.update(AttrDict(pir=False, mag=False))

    with fancysleep:
        # open door
        g.update(AttrDict(pir=False, mag=True))

        gevent.sleep(g.close_delay-1)
        assert no toggled.called
        gevent.sleep(1)

        # garage door close called
        assert toggled.called


def test_garage_autoclose_delayed_by_motion(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)

    g = Garage(toggle)
    # initial setup
    g.update(AttrDict(pir=False, mag=False))

    with fancysleep:
        # open door
        g.update(AttrDict(pir=False, mag=True))

        # advance to 10s before auto-close
        gevent.sleep(g.close_delay-10)

        # signal movement
        g.update(AttrDict(pir=True, mag=True))
        gevent.sleep(1)
        g.update(AttrDict(pir=False, mag=True))

        # wait till past previous auto-close
        gevent.sleep(30)

        assert not toggle.called

        # advanced past motion delay to trigger auto-close
        gevent.sleep(g.motion_delay-30)

        # garage door close called
        assert toggle.called

def test_garage_notify_on_left_open(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=False))

    with fancysleep:
        # open door
        g.update(AttrDict(pir=False, mag=True))

        gevent.sleep(g.notify_delay-1)
        notify.assert_not_called_with("Garage is still open after {mag_open} minutes!")
        gevent.sleep(1)
        notify.assert_called_with("Garage is still open after {mag_open} minutes!")


def test_garage_notify_on_motion(fastsleep, monkeypatch):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=False))

    # motion
    g.update(AttrDict(pir=True, mag=False))

    notify.assert_called_once_with('motion!')


def test_garage_notify_on_door_change():
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=False))

    # door open
    g.update(AttrDict(pir=True, mag=True))

    notify.assert_called_once_with('door open!')
