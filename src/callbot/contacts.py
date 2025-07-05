from csv import DictReader
from pathlib import Path

from loguru import logger as log
from pydantic import ValidationError
from sqlmodel import and_, col, or_, select

from callbot.db import EngineWrapper as DBEngine, Session
from callbot.schemas.contact import Contact, ContactDB


async def import_contacts(path: Path) -> None:
    await DBEngine().create_tables()
    count_total, count_imported, count_invalid = 0, 0, 0
    async with DBEngine().get_session() as session:
        with path.open("r") as csvfile:
            reader = DictReader(csvfile)
            for idx, row in enumerate(reader):
                count_total += 1
                try:
                    contact = Contact.model_validate(row)
                except ValidationError as validation_error:
                    log.error(f"Validation error in line {idx}: {validation_error.json()}")
                    count_invalid += 1
                else:
                    count_imported += await _import_contact(session, contact)
    log.info(f"Imported {count_imported}/{count_total} rows ({count_invalid} invalid)")


async def _import_contact(db_session: Session, contact: Contact) -> bool:
    condition = or_(
        col(ContactDB.phone) == contact.phone,
        and_(
            col(ContactDB.email).is_not(None),
            col(ContactDB.email) == contact.email,
        ),
    )
    results = await db_session.exec(select(ContactDB).where(condition))
    contact_json = contact.model_dump_json(exclude_defaults=True)
    if results.first() is None:
        log.info(f"Importing: {contact_json}")
        db_session.add(contact.to_db())
        await db_session.commit()
        return True
    else:
        log.debug(f"Skipping existing phone/email: {contact_json}")
        return False
