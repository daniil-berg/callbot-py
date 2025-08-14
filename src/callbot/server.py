from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Request, WebSocket, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from loguru import logger as log
# TODO: Migrate to httpx-ws
from websockets import connect as ws_connect

from callbot.auth.jwt import JWT
from callbot.call_manager import CallManager
from callbot.caller import Caller
from callbot.db import EngineWrapper as DBEngine, Session
from callbot.hooks import BeforeStartupHook
from callbot.schemas.amd_status import AMDStatus
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


@app.post("/amdstatus")
async def amd_callback(amd_status: Annotated[AMDStatus, Form()]) -> StrDict:
    settings = Settings()
    if amd_status.account_sid != settings.twilio.account_sid:
        log.error(
            "Possible security breach! Account SID in Twilio AMD status "
            "callback does not match configured SID!"
        )
        return {"status": "error", "message": "Invalid account SID"}
    call_sid = amd_status.call_sid
    call_manager = CallManager.get(call_sid)
    if call_manager is None:
        log.warning(
            f"No active call matches incoming Twilio AMD status SID: {call_sid}"
        )
        return {"status": "error", "message": "No active call with this SID"}
    match amd_status.answered_by:
        case "human":
            log.info(f"Twilio AMD detected human in call {call_sid}")
        case "unknown":
            log.warning(f"Twilio AMD status unknown for call {call_sid}")
        case _:
            call_manager.answering_machine_detected(amd_status)
    return {"status": "ok"}


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    error_str = ""
    if client := request.client:
        error_str += f"{client.host}:{client.port} - "
    error_str += f'"{request.method} {request.url.path}"'
    error_str += f": {exc}"
    log.error(error_str)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )
