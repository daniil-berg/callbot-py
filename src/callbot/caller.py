from fastapi.datastructures import URL
from twilio.rest import Client  # type: ignore[import-untyped]
from twilio.http.async_http_client import AsyncTwilioHttpClient  # type: ignore[import-untyped]
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse  # type: ignore[import-untyped]

from callbot.schemas.contact import Contact
from callbot.settings import Settings


class Caller:
    twilio_client: Client
    endpoint: URL

    def __init__(self) -> None:
        settings = Settings()
        if settings.server.public_base_url is None:
            raise RuntimeError("Missing public base URL")
        public_base_url = URL(str(settings.server.public_base_url))
        self.endpoint = public_base_url.replace(scheme="wss", path="/stream")
        self.twilio_client = Client(
            settings.twilio.account_sid,
            settings.twilio.auth_token.get_secret_value(),
            http_client=AsyncTwilioHttpClient(),
        )

    async def __call__(self, contact: Contact) -> str:
        settings = Settings()
        if settings.twilio.phone_number is None:
            raise RuntimeError("Missing Twilio phone number")
        twiml = VoiceResponse()
        connect = Connect()
        stream = Stream(url=str(self.endpoint))
        for key, value in contact.model_dump(exclude_defaults=True).items():
            stream.parameter(name=key, value=str(value))
        connect.nest(stream)
        twiml.append(connect)
        # TODO: Check https://www.twilio.com/docs/voice/answering-machine-detection
        call_instance = await self.twilio_client.calls.create_async(
            to=contact.phone,
            from_=settings.twilio.phone_number,
            machine_detection="Enable",
            twiml=twiml,
        )
        if not isinstance(call_instance.sid, str):
            raise RuntimeError("Failed to get a call SID!")
        return call_instance.sid
