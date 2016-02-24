import argparse
import asyncio as aio
import asyncio.subprocess as sp
import logging
import logging.config
import os
import re

from aiohttp import web
from pirage import gcm
from pirage.garage import Garage
from pirage.hardware import Monitor
from pirage.util import AttrDict
from . import handlers

# configure logging
config = {
    'version': 1,
    'formatters': {
        'norm': {
            'format': '%(asctime)s:%(levelname)s:>%(name)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'norm',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/pirage.log',
            'mode': 'ab',
            'backupCount': 3,
            'maxBytes': 1024 * 1024,
            'level': 'INFO',
            'formatter': 'norm',
        },
        'webfile': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/pirage.aiohttp.log',
            'mode': 'ab',
            'backupCount': 3,
            'maxBytes': 1024 * 100,
            'formatter': 'norm',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        'pirage': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
        'aiohttp': {
            'handlers': ['webfile'],
            'level': 'DEBUG'
        }
    },
}
logging.config.dictConfig(config)

logger = logging.getLogger(__name__)


def create_app():
    app = web.Application()

    app.router.add_route('GET', '/', handlers.index)
    app.router.add_route('POST', '/click', handlers.click)
    app.router.add_route('POST', '/set_lock', handlers.lock)
    app.router.add_route('POST', '/set_pir', handlers.set_pir)
    app.router.add_route('POST', '/set_notify', handlers.set_notify)
    app.router.add_route('GET', '/stream', handlers.stream)
    app.router.add_route('GET', '/status', handlers.get_status)
    app.router.add_route('GET', '/cam/{type}', handlers.camera)
    app.router.add_static('/static', os.path.join(os.path.dirname(os.path.realpath(__file__)), '../static'),
                          name='static')
    app.router.add_static('/', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates'),
                          name='templates')

    app['cpu_temp'] = 0
    app['notify'] = True
    app['last_push'] = None

    app['clients'] = []

    # create hw monitor
    app['pi'] = Monitor()
    # create garage monitor that uses hw monitor to close garage
    app['garage'] = Garage(lambda *x: aio.ensure_future(app['pi'].toggle_relay()))
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
            proc = await proc
            data = await proc.stdout.read()
            m = re.search(b'\d+(\.\d+)?', data)
            if m:
                app['cpu_temp'] = float(m.group(0))
        except Exception as e:
            logger.warning('cannot get cpu temp: %s', e)

        await aio.sleep(30)


def push_data(data):
    """
    Push a set of data to listening clients, concurrently.
    """
    for q in list(app['clients']):
        aio.ensure_future(q.put(data))


async def gen_data(app):
    """
    Pack data and push to clients.  Send notification if door state changes.
    """
    data = handlers._pack(app)
    push_data(data)

    # notify on mag change?
    logger.debug('last: %s, new: %s', app['last_push'], app['garage'].door_open)
    if app['last_push'] != app['garage'].door_open:
        logger.info("garage changed, %s notification!", "sending" if app['notify'] else "not sending")
        # print(app['notify'])
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
#     logging.info('dweeting %r', data)
#     dweet.report('dat-pi-thang', 'secret-garden-k3y', data)

def do_gcm(data):
    logger.info('sending gcm: %s', data)
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
    finally:
        app['pi'].stop()
        app['garage'].save()


if __name__ == '__main__':
    main()
