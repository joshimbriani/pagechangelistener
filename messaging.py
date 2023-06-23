import firebase_admin
from firebase_admin import messaging

DEFAULT_TOKEN = "eWykbneWQ4GWswCZum1g5S:APA91bFSzZBCTTEWFXzxpGUfK737xDfA1h0wgIOCu6otWzK0CYkFAhoATFcz0rkv6HvWPoBVliPnACTywX0dhXUNqgu6peEuQbHG5yI4BitmyASNewp4tU7SELYgiNK6JxV9ZybqioR_"

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
