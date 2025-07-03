from csv import DictReader
from pathlib import Path

from pydantic import ValidationError
from sqlmodel import and_, col, or_, select

from callbot.db import EngineWrapper as DBEngine, Session
from callbot.schemas.contact import Contact, ContactDB


async def import_contacts(path: Path) -> None:
    await DBEngine().create_tables()
    async with DBEngine().get_session() as session:
        with path.open("r") as csvfile:
            reader = DictReader(csvfile)
            for idx, row in enumerate(reader):
                try:
                    contact = Contact.model_validate(row)
                except ValidationError as validation_error:
                    print(f"Validation error in line {idx}: {validation_error.json()}")
                else:
                    await import_contact(session, contact)


async def import_contact(db_session: Session, contact: Contact) -> None:
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
        print(f"Importing: {contact_json}")
        db_session.add(contact.to_db())
        await db_session.commit()
    else:
        print(f"Skipping existing phone/email: {contact_json}")
