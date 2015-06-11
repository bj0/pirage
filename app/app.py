from flask import Flask, render_template, Response
import time
import json

app = Flask(__name__, static_folder='../static', static_url_path='/static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dan/')
def index2():
    return render_template('index2.html')

@app.route('/click')
def click():
    print 'CLiCK!'

@app.route('/stream')
def stream():
    return Response(gen(), mimetype='text/event-stream')

def gen():
    yield 'retry: 10000\n\n'
    while True:
        yield 'data: {}\n\n'.format(json.dumps(
{
    'times':
    {
        'now':time.time(),
        'last_pir':"25 min",
        'last_mag':"5 min"
    },
    'pir':False,
    'mag':True
}))
        time.sleep(5)


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
