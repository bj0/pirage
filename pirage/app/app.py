from __future__ import absolute_import

import gevent
from gevent import monkey, sleep, spawn
from gevent.queue import Queue
from gevent.pywsgi import WSGIServer
monkey.patch_all()
# import eventlet
# from eventlet import sleep, spawn, wsgi
# from eventlet.queue import Queue
# eventlet.monkey_patch()

from flask import (Flask, render_template, Response, request, jsonify,
                   send_file, stream_with_context)
import time
import json
import subprocess as sp
import re
import argparse
import requests
from StringIO import StringIO

from pirage.hardware import Monitor
from pirage.garage import Garage
from pirage.util import AttrDict
from pirage import dweet, mqtt



def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')

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
    app._hw.register(lambda *x: gen_data())

    app._hw.start()
    # periodically update page
    spawn(poll)
    # periodically get cpu temperature
    spawn(poll_temp)

    return app


def poll_temp():
    while True:
        try:
            temp = sp.check_output('/opt/vc/bin/vcgencmd measure_temp'.split())
            m = re.search('\d+(\.\d+)?', temp)
            if m:
                app._temp = float(m.group(0))
        except Exception as ex:
            print('no temp:', ex)

        sleep(30)


def push_data(data):
    '''
    Push a set of data to listening clients.
    '''
    for q in list(app._clients):
        q.put(data)


def get_data():
    '''
    Grab data from garage and return it in dict format
    '''
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


def gen_data():
    '''
    Generate data to push to clients.
    '''
    data = get_data()
    push_data(data)

    # dweet on mag change?
    if app._last_mag_push != app._g.door_open:
        if app._dweet:
            do_dweet(data)
        do_mqtt(app._g.door_open)
        app._last_mag_push = app._g.door_open

def do_mqtt(door_open):
    try:
        print("mqtt!")
        mqtt.report("pirage/door", door_open)
    except Exception as e:
        print("error mqtting: {}", e)


def do_dweet(data):
    print('dweet!')
    dweet.report('dat-pi-thang', 'secret-garden-k3y', data)


def poll():
    '''
    Periodically update page data.
    '''
    while True:
        gen_data()
        sleep(5)


def gen_fake():
    '''generate fake data'''
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
        sleep(5)

app = create_app()
app.debug = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/click', methods=['POST'])
def click():
    app._g.toggle_door()
    return ""


@app.route('/set_lock', methods=['POST'])
def lock():
    locked = request.json['locked']
    print('set lock:', locked)
    app._g.lock(locked)
    return jsonify(locked=app._g.locked)


@app.route('/set_pir', methods=['POST'])
def set_pir():
    pir = request.get_json()['enabled']
    print('set pir:', pir)
    app._hw.ignore_pir = not pir
    return jsonify(pir_enabled=not app._hw.ignore_pir)


@app.route('/set_dweet', methods=['POST'])
def set_dweet():
    dweet = request.get_json()['enabled']
    print('set dweet:', dweet)
    app._dweet = dweet
    if dweet:
        do_dweet()
    return jsonify(dweet_enabled=app._dweet)


@app.route('/stream')
def stream():
    return Response(get_data_iter(), mimetype='text/event-stream')


@app.route('/status')
def get_status():
    return jsonify(get_data())


@app.route('/cam/<type>')
def camera(type):
    '''
    pull camera image from garage and return it
    '''
    url = "http://admin:taco@10.10.10.102/image/jpeg.cgi"
    # url = "http://10.8.1.89/CGIProxy.fcgi?cmd=snapPicture2&usr=bdat&pwd=bdat&t="
    r = requests.get(url, stream=True)
    buffer = StringIO(r.content)
    buffer.seek(0)
    return send_file(buffer, mimetype='image/jpeg')


def get_data_iter():
    '''
    pull data from queue and send it to the browser.
    '''
    yield 'retry: 10000\n\n'
    q = Queue()
    print('add client')
    app._clients.append(q)
    try:
        while True:
            for data in iter(q.get, 'nan'):
                # print('got data:',data)
                yield 'data: {}\n\n'.format(json.dumps(data))
    finally:
        print('remove client')
        app._clients.remove(q)


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
        WSGIServer((args.host, args.port), app).serve_forever()
    finally:
        app._hw.stop()
        app._g.save()


if __name__ == '__main__':
    main()
