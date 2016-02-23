import json
import logging

import aiohttp
from aiohttp import web
from aiohttp.web import json_response

import asyncio as aio

from pirage.util import asynciter


def index(request):
    return web.HTTPFound(request.app.router['templates'].url(filename='index.html'))


def click(request):
    request.app['garage'].toggle_door()
    return web.Response()


async def lock(request):
    locked = (await request.json())['locked']
    logging.info('set lock:', locked)
    g = request.app['garage']
    g.lock(locked)
    return json_response(dict(locked=g.locked))


async def set_pir(request):
    pir = (await request.json())['enabled']
    logging.info('set pir:', pir)
    pi = request.app['pi']
    pi.ignore_pir = not pir
    return json_response(dict(pir_enabled=not pi.ignore_pir))


async def set_notify(request):
    notify = (await request.json())['enabled']
    logging.info('set notify:', notify)
    request.app['notify'] = notify
    return json_response(dict(notify_enabled=notify))


async def camera(request):
    """
    pull camera image from garage and return it
    """
    url = "http://admin:taco@10.10.10.102/image/jpeg.cgi"
    # url = "http://10.8.1.89/CGIProxy.fcgi?cmd=snapPicture2&usr=bdat&pwd=bdat&t="
    with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return web.Response(body=await response.read())


async def stream(request):
    response = web.StreamResponse(headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    })

    await response.prepare(request)

    logging.info('add stream client')
    q = aio.Queue()
    request.app['clients'].append(q)
    try:
        async for data in _get_aiter(q):
            response.write(data)
    finally:
        logging.info('remove stream client')
        request.app['clients'].remove(q)

    return response


# @app.route('/status')
def get_status(request):
    return json_response(_pack(request.app['garage'].data))



@asynciter
def _get_aiter(q):
    """
    Turn an asyncio.Queue into an EventStream async iterator
    """
    yield b'retry: 10000\n\n'
    while True:
        data = yield from q.get()
        if data == 'nan':
            break
        yield b'data: %b\n\n' % json.dumps(data).encode()


def _pack(app):
    """
    Pack app/garage data into a dict
    """
    data = app['garage'].data
    return {
        'times': {
            'now': data.now,
            'last_pir': data.last_pir_str,
            'last_mag': data.last_mag_str
        },
        'pir': data.pir,
        'mag': data.mag,
        'temp': app['cpu_temp'],
        'locked': app['garage'].locked,
        'pir_enabled': not app['pi'].ignore_pir,
        'notify_enabled': app['notify']
    }