import dweepy
import hmac
import hashlib
import json
import base64

from gevent import sleep


class InvalidDweetError(Exception):
    pass


def calc_mac(key, msg):
    return base64.b64encode(hmac.new(key, msg, hashlib.sha1).digest())


def report(thing, key, data):
    """
    Publish a dweet for a thing.

    key is used to create an hmac
    """
    mac = calc_mac(key, json.dumps(data))
    packet = {'data': data, 'sig': mac}
    print('dweeting for {}!'.format(thing))
    dweepy.dweet_for(thing, packet)


def get_report(thing, key):
    """
    Get the latest dweet for a thing validated by a key.

    If validation fails, throws InvalidDweetError
    """
    dweets = dweepy.get_latest_dweet_for(thing)
    if len(dweets) == 0:
        return None
    dweet = dweets[0]
    if not verify(key, dweet['content']):
        raise InvalidDweetError('verification failed')
    return dweet['content']['data']


def get_reports(thing, key):
    """
    Get a generator that yields dweets for a thing that validate against a key.

    For dweets that don't validate, an InvalidDweetError is yielded
    """
    for dweet in dweepy.listen_for_dweets_from(thing):
        if not verify(key, dweet['content']):
            yield InvalidDweetError('verification failed')
        else:
            yield dweet['content']['data']


def verify(key, packet):
    """
    Verify dweet packet against a key.
    """
    data = packet['data']
    sig = packet['sig']
    mac = calc_mac(key, json.dumps(data))
    return sig == mac
