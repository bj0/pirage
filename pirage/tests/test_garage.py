from __future__ import absolute_import

import pytest
import gevent
import mock

from pirage.util import AttrDict
from pirage.garage import Garage
from .fastsleep import fastsleep, fancysleep

def test_open_when_locked(fancysleep, monkeypatch):
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    toggle = mock.MagicMock()
    g = Garage(toggle)

    # initial setup
    g.lock()
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # open door
        g.update(AttrDict(pir=False, mag=False))

        # an hour later...
        gevent.sleep(60*60)

        # no auto-close
        assert not toggle.called

def test_lock_after_open(fancysleep, monkeypatch):
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    toggle = mock.MagicMock()
    g = Garage(toggle)

    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # open door
        g.update(AttrDict(pir=False, mag=False))

        # after 5 minutes
        gevent.sleep(5*60)

        g.lock()

        # an hour later...
        gevent.sleep(60*60)

        # no auto-close
        assert not toggle.called

def test_unlock_while_closed(fancysleep, monkeypatch):
        monkeypatch.setattr('time.time', lambda: fancysleep.now)
        fancysleep.patch('pirage.garage.sleep')

        toggle = mock.MagicMock()
        g = Garage(toggle)

        # initial setup
        g.lock()
        g.update(AttrDict(pir=False, mag=True))

        with fancysleep:
            gevent.sleep(5)

            g.lock(False)

            # an hour later...
            gevent.sleep(60*60)

            # no auto-close
            assert not toggle.called

def test_unlock_while_open(fancysleep, monkeypatch):
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    toggle = mock.MagicMock()
    g = Garage(toggle)

    # initial setup
    g.lock()
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # open door
        g.update(AttrDict(pir=False, mag=False))

        # after 5 minutes...
        gevent.sleep(5*60)

        g.lock(False)

        # 20 min later...
        gevent.sleep(20*60)

        # auto-close
        assert toggle.called


def test_data(monkeypatch):
    toggle = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: 500)

    g = Garage(toggle)
    g.last_motion = 500-10
    g.last_door_change = 500-300
    g.motion = False
    g.door_open = False

    data = g.data

    assert data.pir == False
    assert data.mag == False
    assert data.last_pir == 10
    assert data.last_mag == 300
    assert data.last_pir_str == '10 sec'
    assert data.last_mag_str == '5 min'

def test_garage_autoclose(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    g.notify = notify
    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # open door
        g.update(AttrDict(pir=False, mag=False))

        gevent.sleep(g.close_delay-1)
        assert not toggle.called

        # make sure warning went out
        assert mock.call('closing garage in {} minutes!'
            .format(g.close_warning/60)) in notify.mock_calls
        gevent.sleep(1)

        # garage door close called
        assert toggle.called

def test_garage_no_autoopen(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    g.notify = notify
    # initial setup
    g.update(AttrDict(pir=False, mag=False))

    with fancysleep:
        gevent.sleep(5)

        # close door
        g.update(AttrDict(pir=False, mag=True))

        gevent.sleep(g.close_delay-1)
        assert not toggle.called

        gevent.sleep(5)

        # garage door close not called
        assert not toggle.called

        gevent.sleep(1000)

        # garage door close not called
        assert not toggle.called


def test_garage_autoclose_delayed_by_motion(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # open door
        g.update(AttrDict(pir=False, mag=False))

        # advance to 10s before auto-close
        gevent.sleep(g.close_delay-10)

        # signal movement
        g.update(AttrDict(pir=True, mag=False))
        gevent.sleep()
        g.update(AttrDict(pir=False, mag=False))

        # wait till past previous auto-close
        gevent.sleep(30)

        assert not toggle.called

        # advanced past motion delay to trigger auto-close
        gevent.sleep(g.motion_delay-30)

        # garage door close called
        assert toggle.called

@pytest.mark.parametrize('pir',[True,False])
def test_garage_notify_on_left_open(fancysleep, monkeypatch, pir):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # open door
        g.update(AttrDict(pir=pir, mag=False))

        gevent.sleep(g.notify_delay-1)
        assert mock.call("Garage is still open after {mag_open} minutes!") not in notify.mock_calls
        gevent.sleep(1)
        notify.assert_called_with("Garage is still open after {mag_open} minutes!")


@pytest.mark.parametrize('mag',[True,False])
def test_garage_notify_on_motion(fastsleep, monkeypatch, mag):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fastsleep.now)
    fastsleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    # motion
    g.update(AttrDict(pir=True, mag=mag))

    notify.assert_called_with('motion!')

@pytest.mark.parametrize('pir',[True,False])
def test_garage_notify_on_door_change(fastsleep, monkeypatch, pir):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fastsleep.now)
    fastsleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    # door open
    g.update(AttrDict(pir=pir, mag=False))

    assert mock.call('door open!') in notify.mock_calls

def test_garage_notify_canceled_after_close(fancysleep, monkeypatch):
    toggle = mock.MagicMock()
    notify = mock.MagicMock()
    monkeypatch.setattr('time.time', lambda: fancysleep.now)
    fancysleep.patch('pirage.garage.sleep')

    g = Garage(toggle)
    g.notify = notify

    # initial setup
    g.update(AttrDict(pir=False, mag=True))

    with fancysleep:
        gevent.sleep(5)

        # door open
        g.update(AttrDict(pir=True, mag=False))

        gevent.sleep(g.notify_delay-20)
        assert mock.call("Garage is still open after {mag_open} minutes!") not in notify.mock_calls

        # close door
        g.update(AttrDict(pir=True, mag=True))
        gevent.sleep(300)
        assert mock.call("Garage is still open after {mag_open} minutes!") not in notify.mock_calls
        print ('WTF',notify.mock_calls)
