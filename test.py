import asyncio as aio

from pirage.channels.rendezvouschannel import RendezvousChannel
from pirage.channels.bufferedchannel import BufferedChannel

q = RendezvousChannel()
# q = BufferedChannel()


async def put(j=0):
    await aio.sleep(0.3)
    for i in range(j, j + 5):
        print(f'putting {i}')
        await q.send(i)
        print(f'pat {i}')

    q.close()


async def test(name=''):
    await aio.sleep(2)
    for i in range(2):
        print(f'{name} getting')
        x = await q.receive()
        print(f'{name} got {x}')
        await aio.sleep(1)


async def test_loop():
    await aio.sleep(0.1)
    print('looping')
    async for i in q:
        print(f'got {i}')

    print('loop ended')


aio.get_event_loop().run_until_complete(
    # aio.gather(put(50), put(), put(30), test('bob'), test("alice"))
    aio.gather(put(), test_loop())
)
print('done')
