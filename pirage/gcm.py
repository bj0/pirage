from gcm import GCM

_gcm = GCM("AIzaSyC4dp-21OdBZfh5foKh4GQuv4xF0z8moqs")

def report(topic, data):
    _gcm.send_topic_message(topic=topic, data=data)
