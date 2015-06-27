import pytest
import gevent
from fastsleep import fastsleep, fancysleep

def test_fancysleep_local_sleep(fancysleep):
    with fancysleep:
        assert fancysleep.now == 0
        gevent.sleep(1)
        assert fancysleep.now == 1
        gevent.sleep(100)
        assert fancysleep.now == 101

def test_fancysleep_local_sleep_block(fancysleep):
    with pytest.raises(gevent.hub.LoopExit):
        gevent.sleep(1)

def test_fancysleep_manual(fancysleep):
    trigger = [False]
    def sleepfun():
        gevent.sleep(5)
        trigger[0] = True

    gt = gevent.spawn(sleepfun)

    assert fancysleep.now == 0
    assert not trigger[0]

    fancysleep.step(4.5)

    assert fancysleep.now == 4.5
    assert not trigger[0]

    fancysleep.step(.5)

    assert fancysleep.now == 5
    assert trigger[0]



def test_fastsleep(fastsleep):
    assert fastsleep.now == 0
    gevent.sleep(5)
    assert fastsleep.now == 5
