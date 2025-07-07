from typing import TypeGuard, TypeVar


_T = TypeVar("_T")


def is_subclass(
    __cls: object,
    __class_or_tuple: type[_T] | tuple[type[_T], ...],
    /,
) -> TypeGuard[type[_T]]:
    """More lenient version of the built-in `issubclass` function."""
    if not isinstance(__cls, type):
        return False
    return issubclass(__cls, __class_or_tuple)
