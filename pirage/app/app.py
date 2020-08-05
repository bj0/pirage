import argparse
import asyncio as aio
import logging.config
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web

from pirage import fcm
from pirage.garage import Garage
from pirage.hardware import Monitor
from pirage.util import AttrDict, create_task
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

    app.router.add_get('/', handlers.index)
    app.router.add_post('/click', handlers.click)
    app.router.add_post('/set_lock', handlers.lock)
    app.router.add_post('/set_pir', handlers.set_pir)
    app.router.add_post('/set_notify', handlers.set_notify)
    app.router.add_get('/stream', handlers.stream)
    app.router.add_get('/status', handlers.get_status)
    app.router.add_get('/cam/{type}', handlers.camera)
    app.router.add_static('/static/', str(Path(__file__) / '../../static'),
                          name='static')

    aiohttp_jinja2.setup(app,
                         loader=jinja2.PackageLoader('pirage.app', 'templates'))

    app['cpu_temp'] = 0
    app['last_push'] = None
    app['clients'] = []

    # create hw monitor
    app['pi'] = Monitor()

    # create garage monitor that uses hw monitor to close garage
    app['garage'] = Garage(lambda *x: create_task(app['pi'].toggle_relay()))

    # load saved state
    extra = app['garage'].load()
    app['notify'] = extra.get('notify', True) # todo unit test loading (with no data)

    # update garage when hw monitor gets changes
    app['pi'].register(app['garage'].update)

    # update page when hw monitor gets changes
    app['pi'].register(lambda *x: create_task(gen_data(app)))

    # start hardware
    app['pi'].start()

    # periodically update page
    create_task(poll(app))
    # periodically get cpu temperature
    create_task(poll_temp())

    return app


async def poll_temp():
    """periodically read processor temperature from /sys/class/thermal"""
    while True:
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'rt') as f:
                data = f.readline()
                if data:
                    app['cpu_temp'] = float(data) / 1e3
                    logger.debug(f'cpu temp: {app["cpu_temp"]}')
        except Exception as e:
            logger.warning('cannot get cpu temp: %s', e)

        await aio.sleep(30)


def push_data(data):
    """
    Push a set of data to listening clients, concurrently.
    """
    for q in list(app['clients']):
        create_task(q.put(data))


async def gen_data(app):
    """
    Pack data and push to clients.  Send notification if door state changes.
    """
    data = handlers._pack(app)
    push_data(data)

    # notify on door change
    logger.debug('last: %s, new: %s', app['last_push'], app['garage'].door_open)
    if app['last_push'] != app['garage'].door_open:
        logger.info("garage changed, %s notification!", "sending" if app['notify'] else "not sending")
        if app['notify']:
            do_fcm(data)
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

def do_fcm(data):
    logger.info('sending fcm: %s', data)
    fcm.report('pirage', data)


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
                        default=kwargs.get('host', '0.0.0.0'))
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
        app['garage'].save(notify=app['notify'])


if __name__ == '__main__':
    main()
