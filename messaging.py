import firebase_admin
from firebase_admin import messaging

DEFAULT_TOKEN = "cH2gHjFgRFCfEHVZvAoXNN:APA91bGHySRpdxckK4of7Y7_fsNmBh__h-7R3wH6837ifw-iQ9Shcxs0mjAhQW_XpAH8izLyYm2Sqf0mYboz0YoOjChzMsZuCjY8a93lvrmTxtgV7QKWopJy-7Dnk3Ai_T3bvooUdpTg"

class Messaging:
    # This is just going to message my phone so no worries keeping the list
    # constant.
    def __init__(self, device_key=DEFAULT_TOKEN):
        self._device_key = device_key

        # Now initialize Firebase.
        # We have the GOOGLE_APPLICATION_CREDENTIAL env variable set.
        self._app = firebase_admin.initialize_app()

    def send_message(self, title, message):
        message = messaging.Message(notification=messaging.Notification(title=title, body=message), token=self._device_key)

        response = messaging.send(message)
