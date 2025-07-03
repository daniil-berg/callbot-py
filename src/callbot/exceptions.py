class CallbotException(Exception):
    pass


class TwilioWebsocketStopReceived(CallbotException):
    pass
