from collections.abc import Sequence
from typing import Any

from pydantic_extra_types import phone_numbers

from callbot.settings import Settings


class PhoneNumberValidator(phone_numbers.PhoneNumberValidator):
    @staticmethod
    def _parse(
        region: str | None,
        number_format: str,
        supported_regions: Sequence[str] | None,
        phone_number: Any,
    ) -> str:
        return phone_numbers.PhoneNumberValidator._parse(
            region or Settings().misc.default_phone_region,
            number_format,
            supported_regions,
            phone_number,
        )
