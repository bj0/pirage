import asyncio as aio
import asyncio.subprocess as sp
import aiohttp
from aiohttp import web
from aiohttp.web import json_response

import os
import json
import re
import argparse
import logging
import logging.handlers

from pirage.hardware import Monitor
from pirage.garage import Garage
from pirage.util import AttrDict, asynciter
from pirage import gcm

logging.basicConfig(level=logging.DEBUG)
handler = logging.handlers.RotatingFileHandler('/tmp/pirage.log', mode='ab', backupCount=3, maxBytes=1024 * 1024)
logging.getLogger().addHandler(handler)


def index(request):
    return web.HTTPFound(request.app.router['templates'].url(filename='index.html'))


def create_app():
    app = web.Application()

    app.router.add_static('/static', os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static'),
                          name='static')
    app.router.add_static('/templates', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates'),
                          name='templates')
    app.router.add_route('GET', '/', index)
    app.router.add_route('POST', '/click', click)
    app.router.add_route('POST', '/set_lock', lock)
    app.router.add_route('POST', '/set_pir', set_pir)
    app.router.add_route('POST', '/set_dweet', set_dweet)
    app.router.add_route('GET', '/stream', stream)
    app.router.add_route('GET', '/status', get_status)
    app.router.add_route('GET', '/cam/{type}', camera)

    app._temp = 0
    app._dweet = False
    app._last_mag_push = None

    app._clients = []

    # create hw monitor
    app._hw = Monitor()
    # create garage monitor that uses hw monitor to close garage
    app._g = Garage(app._hw.toggle_relay)
    app._g.load()
    # update garage when hw monitor gets changes
    app._hw.register(app._g.update)
    # update page when hw monitor gets changes
    app._hw.register(lambda *x: aio.ensure_future(gen_data()))

    app._hw.start()
    # periodically update page
    aio.ensure_future(poll())
    # periodically get cpu temperature
    aio.ensure_future(poll_temp())

    return app


async def poll_temp():
    """periodically read processor temperature using subprocess"""
    while True:
        try:
            proc = aio.create_subprocess_exec(*'/opt/vc/bin/vcgencmd measure_temp'.split(), stdout=sp.PIPE)
            await proc
            data = await proc.stdout.read()
            m = re.search('\d+(\.\d+)?', data)
            if m:
                app._temp = float(m.group(0))
        except Exception:
            logging.warning('cannot get cpu temp', exc_info=True)

        await aio.sleep(30)


def push_data(data):
    """
    Push a set of data to listening clients.
    """
    for q in list(app._clients):
        aio.ensure_future(q.put(data))


def get_data():
    """
    Grab data from garage and return it in dict format
    """
    data = app._g.data
    return {
        'times': {
            'now': data.now,
            'last_pir': data.last_pir_str,
            'last_mag': data.last_mag_str
        },
        'pir': data.pir,
        'mag': data.mag,
        'temp': app._temp,
        'locked': app._g.locked,
        'pir_enabled': not app._hw.ignore_pir,
        'dweet_enabled': app._dweet
    }


async def gen_data():
    """
    Generate data to push to clients.
    """
    data = get_data()
    push_data(data)

    # dweet on mag change?
    if app._last_mag_push != app._g.door_open:
        # if app._dweet:
        # do_dweet(data)
        # do_mqtt(app._g.door_open)
        do_gcm(data)
        app._last_mag_push = app._g.door_open


# def do_mqtt(door_open):
#     try:
#         print("mqtt!")
#         mqtt.report("pirage/door", door_open)
#     except Exception as e:
#         print("error mqtting: {}", e)


# def do_dweet(data):
#     logging.info('dweet!')
#     dweet.report('dat-pi-thang', 'secret-garden-k3y', data)

def do_gcm(data):
    logging.info('gcm!')
    # gcm.report('pirage', data)


async def poll():
    """
    Periodically update page data.
    """
    while True:
        await gen_data()
        await aio.sleep(5)


async def gen_fake():
    """generate fake data"""
    import random
    while True:
        push_data(AttrDict(
            last_pir=random.randint(1, 25),
            last_mag=random.randint(1, 7),
            pir=False,
            mag=True,
            locked=False,
            pir_enabled=True,
            dweet_enabled=False))
        await aio.sleep(5)


# app.debug = True


# def _addroute(f, url, methods=['GET']):
#     app.router.add_route(
#         '*' if len(methods) > 1 else methods[0],
#         url,
#         f
#     )
#     return f
# app.route = _addroute


# @app.route('/')
# def index():
#     return render_template('index.html')


# @app.route('/click', methods=['POST'])
def click(request):
    request.app._g.toggle_door()
    return web.Response()


# @app.route('/set_lock', methods=['POST'])
def lock(request):
    locked = request.json['locked']
    logging.info('set lock:', locked)
    app._g.lock(locked)
    return json_response(dict(locked=app._g.locked))


# @app.route('/set_pir', methods=['POST'])
def set_pir(request):
    pir = request.get_json()['enabled']
    logging.info('set pir:', pir)
    app._hw.ignore_pir = not pir
    return json_response(dict(pir_enabled=not app._hw.ignore_pir))


# @app.route('/set_dweet', methods=['POST'])
def set_dweet(request):
    dweet = request.get_json()['enabled']
    logging.info('set dweet:', dweet)
    app._dweet = dweet
    # if dweet:
    #     do_dweet()
    return json_response(dict(dweet_enabled=app._dweet))


# @app.route('/stream')
async def stream(request):
    response = web.StreamResponse(headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    })

    await response.prepare(request)

    async for data in get_aiter():
        response.write(data)

    return response


# @app.route('/status')
def get_status(request):
    return json_response(get_data())


# @app.route('/cam/{type}')
async def camera(request):
    """
    pull camera image from garage and return it
    """
    # url = "http://admin:taco@10.10.10.102/image/jpeg.cgi"
    url = "http://10.8.1.89/CGIProxy.fcgi?cmd=snapPicture2&usr=bdat&pwd=bdat&t="
    with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return web.Response(body=await response.read())


@asynciter
def get_aiter():
    """
    pull data from queue and send it to the browser.
    """
    yield b'retry: 10000\n\n'
    q = aio.Queue()
    logging.info('add client')
    app._clients.append(q)
    try:
        while True:
            data = yield from q.get()
            if data == 'nan':
                break
            yield b'data: %b\n\n' % json.dumps(data).encode()

    finally:
        logging.info('remove client')
        app._clients.remove(q)


app = create_app()


def main(**kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, help='server port',
                        default=kwargs.get('port', 8245))
    parser.add_argument('--host', help='server host',
                        default=kwargs.get('host', ''))
    parser.add_argument('--no-pir', help='disable pir sensor',
                        action='store_true',
                        default=kwargs.get('no_pir', False))
    parser.add_argument('--lock', help='disable auto closing garage',
                        action='store_true',
                        default=kwargs.get('lock', False))
    parser.add_argument('--dweet', help='dweet door changes',
                        action='store_true',
                        default=kwargs.get('no_dweet', False))
    args = parser.parse_args()

    app._hw._use_pir = not args.no_pir
    app._g.lock(args.lock)
    app._dweet = args.dweet
    try:
        web.run_app(app, host=args.host, port=args.port)
        # WSGIServer((args.host, args.port), app).serve_forever()
    finally:
        app._hw.stop()
        app._g.save()


if __name__ == '__main__':
    main()
