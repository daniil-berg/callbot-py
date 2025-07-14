from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket, status
from fastapi.responses import JSONResponse, Response
from loguru import logger as log
# TODO: Migrate to httpx-ws
from websockets import connect as ws_connect

from callbot.auth.jwt import JWT
from callbot.call_manager import CallManager
from callbot.caller import Caller
from callbot.db import EngineWrapper as DBEngine, Session
from callbot.hooks import BeforeStartupHook
from callbot.schemas.contact import Contact, Phone
from callbot.settings import Settings
from callbot.types import StrDict


SessionDep = Annotated[Session, Depends(DBEngine.yield_session)]
JWTDep = Depends(JWT.decode_and_invalidate)


@asynccontextmanager
async def lifespan(_fastapi: FastAPI) -> AsyncIterator[None]:
    await DBEngine().create_tables()
    await BeforeStartupHook(_fastapi).dispatch()
    yield
    # Potential clean up code here...


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=JSONResponse)
async def root() -> StrDict:
    print(Settings().model_dump_yaml(indent=4))
    return {"status": "ok", "message": "Callbot server is running!"}


@app.websocket("/stream")
async def connect_twilio_to_openai(twilio_ws: WebSocket) -> None:
    """Handle WebSocket connections between Twilio and OpenAI."""
    # TODO: The OpenAI websocket should be opened after the Twilio start message
    #       passes authentication. The entire call manager initialization logic
    #       needs to be reworked.
    await twilio_ws.accept()
    settings = Settings()
    async with ws_connect(
        uri=settings.openai.realtime_stream_url,
        additional_headers=settings.openai.get_realtime_auth_headers(),
    ) as openai_ws:
        call_manager = CallManager(twilio_ws, openai_ws)
        await call_manager.openai_init_session()
        await call_manager.run()


@app.post(
    "/call/{phone_number}",
    dependencies=[JWTDep],
    response_class=JSONResponse,
)
async def make_call(
    phone_number: Phone,
    session: SessionDep,
    response: Response,
) -> StrDict:
    caller = Caller(pool=False)
    try:
        sid = await caller.get_contact_and_call(phone_number, session)
    except ValueError as error:
        log.info(f"No contact with number {phone_number}")
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"status": "error", "message": str(error)}
    log.debug(f"Call SID for {phone_number}: {sid}")
    return {"status": "ok", "sid": sid}


@app.post("/contacts", dependencies=[JWTDep])
async def add_contact(contact: Contact, session: SessionDep) -> Contact:
    contact_db = contact.to_db()
    session.add(contact_db)
    await session.commit()
    await session.refresh(contact_db)
    return Contact.model_validate(contact_db)
