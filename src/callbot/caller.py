from types import TracebackType
from typing import Self, TypeVar

from fastapi.datastructures import URL
from loguru import logger as log
from twilio.rest import Client  # type: ignore[import-untyped]
from twilio.http.async_http_client import AsyncTwilioHttpClient  # type: ignore[import-untyped]
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse  # type: ignore[import-untyped]

from callbot.auth.jwt import JWT
from callbot.db import EngineWrapper as DBEngine, Session
from callbot.schemas.contact import Contact
from callbot.settings import Settings


E = TypeVar("E", bound=BaseException)


class Caller:
    twilio_client: Client
    endpoint: URL

    def __init__(self, *, pool: bool = True) -> None:
        settings = Settings()
        if settings.server.public_base_url is None:
            raise RuntimeError("Missing public base URL")
        public_base_url = URL(str(settings.server.public_base_url))
        self.endpoint = public_base_url.replace(scheme="wss", path="/stream")
        self.twilio_client = Client(
            settings.twilio.account_sid,
            settings.twilio.auth_token.get_secret_value(),
            http_client=AsyncTwilioHttpClient(pool_connections=pool),
        )

    async def __aenter__(self) -> Self:
        """Allows usage of an instance as a context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[E] | None,
        exc_val: E | None,
        exc_tb: TracebackType,
    ) -> None:
        """Exiting the `async with`-block closes the client session."""
        assert isinstance(self.twilio_client.http_client, AsyncTwilioHttpClient)
        await self.twilio_client.http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def __call__(self, contact: Contact) -> str:
        settings = Settings()
        if settings.twilio.phone_number is None:
            raise RuntimeError("Missing Twilio phone number")
        twiml = VoiceResponse()
        connect = Connect()
        stream = Stream(url=str(self.endpoint))
        for key, value in contact.model_dump(exclude_defaults=True).items():
            stream.parameter(name=key, value=str(value))
        stream.parameter(name="token", value=JWT.generate())
        connect.nest(stream)
        twiml.append(connect)
        log.info(f"Calling {contact.phone}: {contact.model_dump_json(exclude_defaults=True)}")
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

    async def get_contact_and_call(
        self,
        phone_number: str,
        db_session: Session | None = None,
    ) -> str:
        select_statement = Contact.select_by_phone(phone_number)
        close_session = False
        if db_session is None:
            close_session = True
            db_session = DBEngine().get_session()
        try:
            results = await db_session.exec(select_statement)
            if not (contact := results.first()):
                raise ValueError("Contact not found")
        finally:
            if close_session:
                await db_session.close()
        return await self(contact)
