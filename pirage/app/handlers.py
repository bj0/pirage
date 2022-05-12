import io
import json
import logging
import time

import asks
import trio
from pirage.hardware import read_temp, Hardware
from quart import Blueprint, render_template, send_file

logger = logging.getLogger(__name__)

bp = Blueprint('app', __name__)

pi = Hardware()


@bp.route('/')
async def index():
    """
    get the root index (main page)
    """
    return await render_template('index.html')


@bp.route('/click', methods=['POST'])
async def click():
    """
    toggles the garage door
    """
    logger.info('click')
    await pi.toggle_relay()
    return '', 204


# @bp.route('/set_lock')
# async def lock(request):
#     """
#     set garage door lock
#     :param request:
#     :return:
#     """
#     locked = (await request.json())['locked']
#     logger.info(f'set lock: {locked}')
#     # g = request.app['garage']
#     # g.lock(locked)
#     return dict(locked=g.locked)


# @bp.route('/set_pir')
# async def set_pir(request):
#     """
#     set pir sensor on/off
#     :param request:
#     :return:
#     """
#     pir = (await request.json())['enabled']
#     logger.info(f'set pir: {pir}')
#     pi = request.app['pi']
#     pi.ignore_pir = not pir
#     return dict(pir_enabled=not pi.ignore_pir)


# @bp.route('/set_notify')
# async def set_notify(request):
#     """
#     set notification pushing on/off
#     :param request:
#     :return:
#     """
#     notify = (await request.json())['enabled']
#     logger.info(f'set notify: {notify}')
#     request.app['notify'] = notify
#     return dict(notify_enabled=notify)


@bp.route('/cam/<image>')
async def camera(image):
    """
    pull camera image from garage and return it
    """
    logger.info(f'camera: {image}')
    url = "http://10.10.10.137/image/jpeg.cgi"
    # url = "http://10.8.1.89/CGIProxy.fcgi?cmd=snapPicture2&usr=bdat&pwd=bdat&t="
    # for some reason simply returning the raw data doesn't work anymore, so i have to wrap it in BytesIO and send_file it
    # return Response((await asks.get(url, auth=asks.BasicAuth(('admin', 'taco')))).raw, mimetype="image/jpeg", content_type="image/jpeg")
    return await send_file(
        io.BytesIO((await asks.get(url, auth=asks.BasicAuth(('admin', 'taco')))).raw),
        mimetype="image/jpeg")


@bp.route('/stream')
async def stream():
    """
    get a SSE session for live status updates
    :param request:
    :return:
    """

    async def send_events():
        yield b'retry: 10000\n\n'
        while True:
            data = _pack()
            yield f'data: {json.dumps(data)}\n\n'.encode('utf-8')
            await trio.sleep(3)

    return send_events(), {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Transfer-Encoding': 'chunked',
    }


@bp.route('/status')
def get_status():
    """
    get current garage status
    :param request:
    :return:
    """
    logger.info('status')
    return _pack()


def _pack():
    """
    Pack app/garage data into a dict
    """
    sensors = pi.read_sensors()
    temp = read_temp()
    return {
        'times': {
            'now': time.time(),
            'last_pir': "?",
            'last_mag': "?"
        },
        'pir': sensors.pir,
        'mag': sensors.mag,
        'temp': temp,
        'locked': False,
        'pir_enabled': not pi.ignore_pir,
        'notify_enabled': False
    }
