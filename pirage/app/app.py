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


from flask import Flask, render_template, Response
import time
import json
import subprocess as sp
import re

from pirage.hardware import Monitor
from pirage.garage import Garage
from pirage.util import AttrDict

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    # app._q = Queue()

    #TODO start hardware monitoring
    #TODO start history/triggers watching

    app._temp = 0
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
    # spawns fake data greenlet
    # spawn(gen)
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
        q.put({
            'times': {
                'now':data.now,
                'last_pir':data.last_pir_str,
                'last_mag':data.last_mag_str
            },
            'pir': data.pir,
            'mag': data.mag,
            'temp': app._temp
        })

def gen_data():
    '''
    Generate data to push to clients.
    '''
    data = app._g.data
    push_data(data)

    # dweet on mag change?
    if app._last_mag_push != app._g.door_open:
        #dweet.report('dat_pi_thang','secret-garden-k3y',data)
        app._last_mag_push = app._g.door_open

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
            last_pir=random.randint(1,25),
            last_mag=random.randint(1,7),
            pir=False,
            mag=True))
        sleep(5)

app = create_app()
app.debug = True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dan/')
def index2():
    return render_template('index2.html')

@app.route('/click', methods=['POST'])
def click():
    app._g.toggle_door()
    return ""

@app.route('/stream')
def stream():
    return Response(get_data(), mimetype='text/event-stream')

def get_data():
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
                print('got data:',data)
                yield 'data: {}\n\n'.format(json.dumps(data))
    finally:
        print('remove client')
        app._clients.remove(q)

def main():
    # app.run(port=8245, debug=True)
    try:
        WSGIServer(('',8245), app).serve_forever()
    finally:
        app._hw.stop()
        app._g.save()
    # wsgi.server(eventlet.listen(('',8245)), app)


if __name__ == '__main__':
    main()
