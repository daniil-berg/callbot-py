from typing import Annotated

from pydantic import BeforeValidator, EmailStr, validate_call
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

    def __str__(self) -> str:
        output = f"{self.salutation} {self.firstname} {self.lastname}"
        if self.company:
            if self.role:
                output += f" ({self.role} @ {self.company})"
            else:
                output += f" ({self.company})"
        return output

    @property
    def full_name(self) -> str:
        return f"{self.firstname} {self.lastname}"

    def to_db(self) -> "ContactDB":
        return ContactDB.model_validate(self)

    @staticmethod
    @validate_call
    def select_by_phone(phone: Phone) -> SelectOfScalar["ContactDB"]:
        condition = col(ContactDB.phone) == phone
        return select(ContactDB).where(condition)


class ContactDB(Contact, table=True):
    __tablename__ = "contact"
