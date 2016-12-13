import pytest
import asyncio as aio
from .aiofastsleep import fastsleep, fancysleep

@pytest.mark.asyncio
async def test_fancysleep_local_sleep(fancysleep):
    with fancysleep:
        assert fancysleep.now == 0
        await aio.sleep(1)
        assert fancysleep.now == 1
        await aio.sleep(100)
        assert fancysleep.now == 101
        await fancysleep.step(3)
        assert fancysleep.now == 104

@pytest.mark.asyncio
async def test_fancysleep_local_sleep_noblock(fancysleep):
    with fancysleep:
        # does not raise
        await aio.wait_for(aio.sleep(10), 0.01)

@pytest.mark.asyncio
async def test_fancysleep_local_sleep_block(fancysleep):
    with pytest.raises(aio.TimeoutError):
        # blocks, so raises timeout
        await aio.wait_for(aio.sleep(10), 0.01)

@pytest.mark.asyncio
async def test_fancysleep_local_sleepa(fancysleep):
    async with fancysleep:
        assert fancysleep.now == 0
        await aio.sleep(1)
        assert fancysleep.now == 1
        await aio.sleep(100)
        assert fancysleep.now == 101
        await fancysleep.step(3)
        assert fancysleep.now == 104

@pytest.mark.asyncio
async def test_fancysleep_local_sleep_noblocka(fancysleep):
    async with fancysleep:
        # does not raise
        await aio.wait_for(aio.sleep(10), 0.01)


@pytest.mark.asyncio
async def test_fancysleep_manual(fancysleep):
    trigger = [False]
    async def sleepfun():
        await aio.sleep(5)
        trigger[0] = True

    task = aio.ensure_future(sleepfun())

    assert fancysleep.now == 0
    assert not trigger[0]

    await fancysleep.step(4.5)

    assert fancysleep.now == 4.5
    assert not trigger[0]

    await fancysleep.step(.5)

    assert fancysleep.now == 5
    assert trigger[0]

@pytest.mark.asyncio
async def test_fancysleep_order(fancysleep):
    with fancysleep:
        t1 = aio.ensure_future(aio.sleep(20)) # starts "immediately"
        t2 = aio.sleep(5) # doesn't start until awaited
        await aio.sleep(1)
        await t2 # started at 1
        assert fancysleep.now == 6
        await t1 # started at 0
        assert fancysleep.now == 20

@pytest.mark.asyncio
async def test_fancysleep_ordera(fancysleep):
    async with fancysleep:
        t1 = aio.ensure_future(aio.sleep(20)) # starts "immediately"
        t2 = aio.sleep(5) # doesn't start until awaited
        await aio.sleep(1)
        await t2 # started at 1
        assert fancysleep.now == 6
        await t1 # started at 0
        assert fancysleep.now == 20

@pytest.mark.asyncio
async def test_fastsleep(fastsleep):
    assert fastsleep.now == 0
    await aio.sleep(5)
    assert fastsleep.now == 5
