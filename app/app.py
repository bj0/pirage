import gevent
from gevent import monkey, sleep, spawn
from gevent.queue import Queue
from gevent.pywsgi import WSGIServer
monkey.patch_all()

from flask import Flask, render_template, Response
import time
import json

def create_app():
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    app._q = Queue()

    return app

app = create_app()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dan/')
def index2():
    return render_template('index2.html')

@app.route('/click', methods=['POST'])
def click():
    print('CLiCK!')
    return ""

@app.route('/stream')
def stream():
    return Response(get_data(app._q), mimetype='text/event-stream')

def get_data(q):
    yield 'retry: 10000\n\n'
    while True:
        for data in q:
            print('got data:',data)
            yield 'data: {}\n\n'.format(json.dumps(data))

def gen():
    '''generate fake data'''
    import random
    while True:
        app._q.put({
            'times': {
                'now':time.time(),
                'last_pir':"{} min".format(random.randint(1,25)),
                'last_mag':"{} min".format(random.randint(1,7 ))
                },
            'pir':False,
            'mag':True
            })
        sleep(5)


if __name__ == '__main__':

    #TODO start hardware monitoring
    #TODO start history/triggers watching
    spawn(gen)
    #app.run(port=8245, debug=True, threaded=False)
    WSGIServer(('',8245), app).serve_forever()
