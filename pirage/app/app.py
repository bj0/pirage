import logging.config

import trio
from clii import App
from hypercorn.config import Config
from hypercorn.trio import serve
from pirage import fcm
from quart_trio import QuartTrio

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
            'filename': '/tmp/pirage.web.log',
            'mode': 'ab',
            'backupCount': 3,
            'maxBytes': 1024 * 100,
            'formatter': 'norm',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        '*': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
        'pirage': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
        '': {
            'handlers': ['webfile'],
            'level': 'DEBUG'
        }
    },
}
logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

_cli = App()


def create_app():
    app = QuartTrio(__name__)

    from pirage.app.handlers import bp
    app.register_blueprint(bp)

    # app['cpu_temp'] = 0
    # app['last_push'] = None
    # app['clients'] = []

    # create hw monitor
    # app['pi'] = Hardware()

    # create garage monitor that uses hw monitor to close garage
    # app['garage'] = Garage(lambda *x: create_task(app['pi'].toggle_relay()))

    # load saved state
    # extra = app['garage'].load()
    # app['notify'] = extra.get('notify', True)  # todo unit test loading (with no data)

    # update garage when hw monitor gets changes
    # app['pi'].register(app['garage'].update)

    # update page when hw monitor gets changes
    # app['pi'].register(lambda *x: create_task(gen_data(app)))

    # start hardware
    # app['pi'].start()

    return app


# def push_data(data):
#     """
#     Push a set of data to listening clients, concurrently.
#     """
#     for q in list(app['clients']):
#         create_task(q.put(data))


# async def gen_data(app):
#     """
#     Pack data and push to clients.  Send notification if door state changes.
#     """
#     data = handlers._pack(app)
#     push_data(data)
#
#     # notify on door change
#     logger.debug('last: %s, new: %s', app['last_push'], app['garage'].door_open)
#     if app['last_push'] != app['garage'].door_open:
#         logger.info("garage changed, %s notification!", "sending" if app['notify'] else "not sending")
#         if app['notify']:
#             do_fcm(data)
#         app['last_push'] = app['garage'].door_open


def do_fcm(data):
    logger.info('sending fcm: %s', data)
    fcm.report('pirage', data)


# async def poll(app):
#     """
#     Periodically update page data.
#     """
#     while True:
#         await gen_data(app)
#         await aio.sleep(5)


# async def gen_fake():
#     """generate fake data"""
#     import random
#     while True:
#         push_data(AttrDict(
#             last_pir=random.randint(1, 25),
#             last_mag=random.randint(1, 7),
#             pir=False,
#             mag=True,
#             locked=False,
#             pir_enabled=True,
#             notify_enabled=False))
#         await aio.sleep(5)


@_cli.main
async def main(host: str = "0.0.0.0", port: int = 8245):
    """
    async entry point.
    """
    app = create_app()
    config = Config()
    config.bind = [f"{host}:{port}"]
    async with trio.open_nursery() as nursery:
        # nursery.start_soon(poll_temp, app)
        # direct run for debugging
        # nursery.start_soon(app.run_task)
        # start hypercorn server in trio's loop
        nursery.start_soon(serve, app, config)
        # todo other stuff...


def cli():
    """synchronous entry point (run from terminal)"""
    # run the clii entry point in trio's event loop
    trio.run(_cli.run)


# @cli.main
# def main(**kwargs):
#     trio.run(amain)
# parser = argparse.ArgumentParser()
# parser.add_argument('-p', '--port', type=int, help='server port',
#                     default=kwargs.get('port', 8245))
# parser.add_argument('--host', help='server host',
#                     default=kwargs.get('host', '0.0.0.0'))
# parser.add_argument('--no-pir', help='disable pir sensor',
#                     action='store_true',
#                     default=kwargs.get('no_pir', False))
# parser.add_argument('--lock', help='disable auto closing garage',
#                     action='store_true',
#                     default=kwargs.get('lock', True))
# parser.add_argument('--notify', help='push door change notifications',
#                     action='store_true',
#                     default=kwargs.get('no_notify', True))
# args = parser.parse_args()
#
# # app['pi'].ignore_pir = args.no_pir
# # app['garage'].lock(args.lock)
# # app['notify'] = args.notify
# try:
#     app.run(host=args.host, port=args.port)
#     # web.run_app(app, host=args.host, port=args.port)
# finally:
#     # app['pi'].stop()
#     # app['garage'].save(notify=app['notify'])
#     app.run()


if __name__ == '__main__':
    cli()
    # main()
    # trio.run(amain)
