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
from pirage.util import AttrDict
from pirage import gcm

from . import handlers

logging.basicConfig(level=logging.DEBUG)
handler = logging.handlers.RotatingFileHandler('/tmp/pirage.log', mode='ab', backupCount=3, maxBytes=1024 * 1024)
handler.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logging.getLogger().addHandler(ch)
logging.getLogger().addHandler(handler)


def create_app():
    app = web.Application()

    app.router.add_static('/static', os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static'),
                          name='static')
    app.router.add_static('/templates', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates'),
                          name='templates')
    app.router.add_route('GET', '/', handlers.index)
    app.router.add_route('POST', '/click', handlers.click)
    app.router.add_route('POST', '/set_lock', handlers.lock)
    app.router.add_route('POST', '/set_pir', handlers.set_pir)
    app.router.add_route('POST', '/set_notify', handlers.set_notify)
    app.router.add_route('GET', '/stream', handlers.stream)
    app.router.add_route('GET', '/status', handlers.get_status)
    app.router.add_route('GET', '/cam/{type}', handlers.camera)

    app['cpu_temp'] = 0
    app['notify'] = True
    app['last_push'] = None

    app['clients'] = []

    # create hw monitor
    app['pi'] = Monitor()
    # create garage monitor that uses hw monitor to close garage
    app['garage'] = Garage(app['pi'].toggle_relay)
    app['garage'].load()
    # update garage when hw monitor gets changes
    app['pi'].register(app['garage'].update)
    # update page when hw monitor gets changes
    app['pi'].register(lambda *x: aio.ensure_future(gen_data(app)))

    app['pi'].start()
    # periodically update page
    aio.ensure_future(poll(app))
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
    for q in list(app['clients']):
        aio.ensure_future(q.put(data))


async def gen_data(app):
    """
    Generate data to push to clients.
    """
    data = handlers._pack(app)
    push_data(data)

    # notify on mag change?
    print('last: ', app['last_push'], app['garage'].door_open)
    if app['last_push'] != app['garage'].door_open:
        print(app['notify'])
        if app['notify']:
            do_gcm(data)
        app['last_push'] = app['garage'].door_open


# def do_mqtt(door_open):
#     try:
#         print("mqtt: {}", door_open)
#         mqtt.report("pirage/door", door_open)
#     except Exception as e:
#         print("error mqtting: {}", e)


# def do_dweet(data):
#     logging.info('dweeting {}', data)
#     dweet.report('dat-pi-thang', 'secret-garden-k3y', data)

def do_gcm(data):
    logging.info('sending gcm: {}', data)
    print('gcm')
    gcm.report('pirage', data)


async def poll(app):
    """
    Periodically update page data.
    """
    while True:
        await gen_data(app)
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
            notify_enabled=False))
        await aio.sleep(5)


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
    parser.add_argument('--notify', help='push door change notifications',
                        action='store_true',
                        default=kwargs.get('no_notify', True))
    args = parser.parse_args()

    app['pi'].ignore_pir = args.no_pir
    app['garage'].lock(args.lock)
    app['notify'] = args.notify
    try:
        web.run_app(app, host=args.host, port=args.port)
        # WSGIServer((args.host, args.port), app).serve_forever()
    finally:
        app['pi'].stop()
        app['garage'].save()


if __name__ == '__main__':
    main()
