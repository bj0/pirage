from pyfcm import FCMNotification as FCM

_fcm = FCM("AIzaSyC4dp-21OdBZfh5foKh4GQuv4xF0z8moqs")


def report(topic, data):
    _fcm.notify_topic_subscribers(topic, data_message=data)
