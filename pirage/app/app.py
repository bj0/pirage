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

from pirage.hardware import Monitor
from pirage.garage import Garage
from priage.util import AttrDict

clients = []

# create hw monitor
hw = Monitor()
# create garage monitor that uses hw monitor to close garage
g = Garage(hw.toggle_relay)
# update garage when hw monitor gets changes
hw.register(g.update)
# update page when hw monitor gets changes
hw.register(lambda *x: gen_data())

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    # app._q = Queue()

    #TODO start hardware monitoring
    #TODO start history/triggers watching

    hw.start()
    # periodically update page
    spawn(poll)
    # spawns fake data greenlet
    # spawn(gen)

    return app

def push_data(data):
    '''
    Push a set of data to listening clients.
    '''
    for q in list(clients):
        q.put({
            'times': {
                'now':int(time.time()),
                'last_pir':data.last_pir,
                'last_mag':data.last_mag
            },
            'pir': data.pir,
            'mag': data.mag
        })

def gen_data():
    '''
    Generate data to push to clients.
    '''
    last_pir = '{} min'.format((g.last_motion or 0)/60)
    last_mag = '{} min'.format((g.last_door_change or 0)/60)
    push_data(AttrDict(
        last_pir=last_pir,
        last_mag=last_mag,
        pir=g.motion, mag = g.door_open
    ))

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
    print('click!')
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
    clients.append(q)
    try:
        while True:
            for data in iter(q.get, 'nan'):
                print('got data:',data)
                yield 'data: {}\n\n'.format(json.dumps(data))
    finally:
        print('remove client')
        clients.remove(q)

def main():
    # app.run(port=8245, debug=True)
    try:
        WSGIServer(('',8245), app).serve_forever()
    finally:
        hw.stop()
    # wsgi.server(eventlet.listen(('',8245)), app)


if __name__ == '__main__':
    main()
