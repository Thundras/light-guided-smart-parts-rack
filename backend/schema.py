from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

Validator = Callable[[Any, str, str], None]


class SchemaValidationError(ValueError):
    pass


def validate_list_payload(
    payload: Any, item_validator: Callable[[Any, str, str], None], source: str
) -> None:
    if not isinstance(payload, list):
        _raise(source, f"expected list, got {type(payload).__name__}")
    for index, item in enumerate(payload):
        item_validator(item, source, f"item {index}")


def validate_rack(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("id", _validate_string),
            ("name", _validate_string),
            ("wledInstance", _validate_string),
            ("rows", _validate_int),
            ("drawersPerRow", _validate_int),
        ],
    )


def validate_drawer(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("id", _validate_string),
            ("rackId", _validate_string),
            ("row", _validate_int),
            ("col", _validate_int),
            ("label", _validate_string),
            ("pixelRange", _validate_pixel_range),
        ],
    )


def validate_part(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("id", _validate_string),
            ("name", _validate_string),
            ("categoryId", _validate_string),
            ("manufacturerId", _validate_string),
            ("drawerId", _validate_string),
            ("tags", _validate_list_of_strings),
            ("quantity", _validate_int),
        ],
        optional=[
            ("notes", _validate_optional_string),
            ("images", _validate_list_of_strings),
        ],
    )


def validate_category(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[("id", _validate_string), ("name", _validate_string)],
    )


def validate_manufacturer(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[("id", _validate_string), ("name", _validate_string)],
    )


def validate_tag(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[("id", _validate_string), ("name", _validate_string)],
    )


def validate_location(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[("id", _validate_string), ("name", _validate_string)],
        optional=[("description", _validate_optional_string)],
    )


def validate_stock_movement(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("id", _validate_string),
            ("partId", _validate_string),
            ("type", _validate_string),
            ("qty", _validate_int),
            ("timestamp", _validate_string),
        ],
        optional=[("note", _validate_optional_string)],
    )


def validate_adjustment(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("id", _validate_string),
            ("partId", _validate_string),
            ("delta", _validate_int),
            ("timestamp", _validate_string),
        ],
        optional=[("reason", _validate_optional_string)],
    )


def validate_reservation(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("id", _validate_string),
            ("partId", _validate_string),
            ("qty", _validate_int),
            ("status", _validate_string),
            ("timestamp", _validate_string),
        ],
        optional=[("note", _validate_optional_string)],
    )


def validate_parts_by_tag(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[("tagId", _validate_string), ("partIds", _validate_list_of_strings)],
    )


def validate_parts_by_category(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[
            ("categoryId", _validate_string),
            ("partIds", _validate_list_of_strings),
        ],
    )


def validate_parts_by_drawer(item: Any, source: str, location: str) -> None:
    _validate_fields(
        item,
        source,
        location,
        required=[("drawerId", _validate_string), ("partIds", _validate_list_of_strings)],
    )


def _validate_fields(
    data: Any,
    source: str,
    location: str,
    required: Sequence[tuple[str, Validator]],
    optional: Sequence[tuple[str, Validator]] | None = None,
) -> None:
    if not isinstance(data, dict):
        _raise(source, f"{location} expected object, got {type(data).__name__}")

    optional = optional or []
    allowed_fields = {name for name, _ in required} | {name for name, _ in optional}
    for field in data:
        if field not in allowed_fields:
            _raise(source, f"{location} has unexpected field '{field}'")

    for field, validator in required:
        if field not in data:
            _raise(source, f"{location} missing required field '{field}'")
        validator(data[field], source, f"{location} field '{field}'")

    for field, validator in optional:
        if field in data:
            validator(data[field], source, f"{location} field '{field}'")


def _validate_string(value: Any, source: str, location: str) -> None:
    if not isinstance(value, str):
        _raise(source, f"{location} expected string, got {type(value).__name__}")


def _validate_optional_string(value: Any, source: str, location: str) -> None:
    if value is not None and not isinstance(value, str):
        _raise(source, f"{location} expected string or null, got {type(value).__name__}")


def _validate_int(value: Any, source: str, location: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(source, f"{location} expected integer, got {type(value).__name__}")


def _validate_list_of_strings(value: Any, source: str, location: str) -> None:
    if not isinstance(value, list):
        _raise(source, f"{location} expected list of strings, got {type(value).__name__}")
    for index, item in enumerate(value):
        if not isinstance(item, str):
            _raise(
                source,
                f"{location}[{index}] expected string, got {type(item).__name__}",
            )


def _validate_pixel_range(value: Any, source: str, location: str) -> None:
    _validate_fields(
        value,
        source,
        location,
        required=[("start", _validate_int), ("count", _validate_int)],
    )


def _raise(source: str, message: str) -> None:
    raise SchemaValidationError(f"Validation error in {source}: {message}")
