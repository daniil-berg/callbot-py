from typing import Annotated

from pydantic import BeforeValidator, EmailStr
from sqlmodel import Field, SQLModel, col, select
from sqlmodel.sql.expression import SelectOfScalar

from callbot.misc.phone_number import PhoneNumberValidator


EmptyStrAsNone = BeforeValidator(lambda v: None if v == "" else v)

Phone = Annotated[str, PhoneNumberValidator(number_format="E164")]
Email = Annotated[EmailStr | None, EmptyStrAsNone]


class Contact(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    company: str
    firstname: str
    lastname: str
    phone: Phone = Field(unique=True)
    email: Email = Field(default=None, unique=True)
    salutation: str = ""
    title: str = ""
    role: str = ""

    def to_db(self) -> "ContactDB":
        return ContactDB.model_validate(self)

    @classmethod
    def select_by_phone(cls, phone: str) -> SelectOfScalar["ContactDB"]:
        condition = col(ContactDB.phone) == phone
        return select(ContactDB).where(condition)


class ContactDB(Contact, table=True):
    __tablename__ = "contact"
