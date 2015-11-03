import paho.mqtt.client as mqtt
from contextlib import contextmanager
from threading import Event
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

def report(subject, data, host="bird.mx"):
    '''
    send an mqtt message to bird
    '''
    client = mqtt.Client("pirage-pub")
    client.connect(host)
    client.publish(subject, data)

@contextmanager
def get_report_queue(subject, host="bird.mx"):
    '''
    return a queue that gets filled by an mqtt
    client subscribed to bird
    '''
    q = Queue()
    e = Event()
    def on_connect(client, *x):
        client.subscribe(subject)
        e.set()
    def on_message(client, userdata, msg):
        q.put((msg.topic,str(msg.payload)))

    client = mqtt.Client("pirage-sub")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(host)
    client.loop_start()

    # wait until ready
    e.wait(1)
    yield q

    client.disconnect()
