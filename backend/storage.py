from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping, Sequence, TypeVar

from .models import (
    Adjustment,
    Category,
    Drawer,
    Location,
    Manufacturer,
    Part,
    PartsByCategory,
    PartsByDrawer,
    PartsByTag,
    Rack,
    Reservation,
    StockMovement,
    Tag,
)

T = TypeVar("T")
Validator = Callable[[Any, str], None]


def _raise_validation_error(path: str, message: str) -> None:
    raise ValueError(f"Invalid JSON schema at {path}: {message}")


def _validate_type(value: Any, expected: type | tuple[type, ...], path: str) -> None:
    if not isinstance(value, expected):
        if isinstance(expected, tuple):
            expected_name = " or ".join(item.__name__ for item in expected)
        else:
            expected_name = expected.__name__
        _raise_validation_error(path, f"expected {expected_name}, got {type(value).__name__}")


def _validate_list(value: Any, item_validator: Validator, path: str) -> None:
    _validate_type(value, list, path)
    for index, item in enumerate(value):
        item_validator(item, f"{path}[{index}]")


def _validate_optional(value: Any, validator: Validator, path: str) -> None:
    if value is None:
        return
    validator(value, path)


def _validate_dict(
    value: Any,
    required_fields: Mapping[str, Validator],
    optional_fields: Mapping[str, Validator],
    path: str,
) -> None:
    _validate_type(value, dict, path)
    missing = [key for key in required_fields if key not in value]
    if missing:
        _raise_validation_error(path, f"missing required keys: {', '.join(missing)}")
    allowed = set(required_fields) | set(optional_fields)
    extras = [key for key in value if key not in allowed]
    if extras:
        _raise_validation_error(path, f"unexpected keys: {', '.join(extras)}")
    for key, validator in required_fields.items():
        validator(value[key], f"{path}.{key}")
    for key, validator in optional_fields.items():
        if key in value:
            validator(value[key], f"{path}.{key}")


def _validate_str(value: Any, path: str) -> None:
    _validate_type(value, str, path)


def _validate_int(value: Any, path: str) -> None:
    _validate_type(value, int, path)


def _validate_str_list(value: Any, path: str) -> None:
    _validate_list(value, _validate_str, path)


def _validate_pixel_range(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={"start": _validate_int, "count": _validate_int},
        optional_fields={},
        path=path,
    )


def _validate_rack(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={
            "id": _validate_str,
            "name": _validate_str,
            "wledInstance": _validate_str,
            "rows": _validate_int,
            "drawersPerRow": _validate_int,
        },
        optional_fields={},
        path=path,
    )


def _validate_drawer(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={
            "id": _validate_str,
            "rackId": _validate_str,
            "row": _validate_int,
            "col": _validate_int,
            "label": _validate_str,
            "pixelRange": _validate_pixel_range,
        },
        optional_fields={},
        path=path,
    )


def _validate_part(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={
            "id": _validate_str,
            "name": _validate_str,
            "categoryId": _validate_str,
            "manufacturerId": _validate_str,
            "drawerId": _validate_str,
            "quantity": _validate_int,
        },
        optional_fields={
            "tags": _validate_str_list,
            "notes": lambda item, item_path: _validate_optional(item, _validate_str, item_path),
            "images": _validate_str_list,
        },
        path=path,
    )


def _validate_category(value: Any, path: str) -> None:
    _validate_dict(value, required_fields={"id": _validate_str, "name": _validate_str}, optional_fields={}, path=path)


def _validate_manufacturer(value: Any, path: str) -> None:
    _validate_dict(value, required_fields={"id": _validate_str, "name": _validate_str}, optional_fields={}, path=path)


def _validate_tag(value: Any, path: str) -> None:
    _validate_dict(value, required_fields={"id": _validate_str, "name": _validate_str}, optional_fields={}, path=path)


def _validate_location(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={"id": _validate_str, "name": _validate_str},
        optional_fields={
            "description": lambda item, item_path: _validate_optional(item, _validate_str, item_path),
        },
        path=path,
    )


def _validate_stock_movement(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={
            "id": _validate_str,
            "partId": _validate_str,
            "type": _validate_str,
            "qty": _validate_int,
            "timestamp": _validate_str,
        },
        optional_fields={
            "note": lambda item, item_path: _validate_optional(item, _validate_str, item_path),
        },
        path=path,
    )


def _validate_adjustment(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={
            "id": _validate_str,
            "partId": _validate_str,
            "delta": _validate_int,
            "timestamp": _validate_str,
        },
        optional_fields={
            "reason": lambda item, item_path: _validate_optional(item, _validate_str, item_path),
        },
        path=path,
    )


def _validate_reservation(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={
            "id": _validate_str,
            "partId": _validate_str,
            "qty": _validate_int,
            "status": _validate_str,
            "timestamp": _validate_str,
        },
        optional_fields={
            "note": lambda item, item_path: _validate_optional(item, _validate_str, item_path),
        },
        path=path,
    )


def _validate_parts_by_tag(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={"tagId": _validate_str, "partIds": _validate_str_list},
        optional_fields={},
        path=path,
    )


def _validate_parts_by_category(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={"categoryId": _validate_str, "partIds": _validate_str_list},
        optional_fields={},
        path=path,
    )


def _validate_parts_by_drawer(value: Any, path: str) -> None:
    _validate_dict(
        value,
        required_fields={"drawerId": _validate_str, "partIds": _validate_str_list},
        optional_fields={},
        path=path,
    )


@dataclass(frozen=True)
class MasterDataPaths:
    racks: Path
    drawers: Path
    parts: Path
    categories: Path
    manufacturers: Path
    tags: Path
    locations: Path

    @classmethod
    def from_root(cls, root: Path) -> "MasterDataPaths":
        master_root = root / "data" / "master"
        return cls(
            racks=master_root / "racks.json",
            drawers=master_root / "drawers.json",
            parts=master_root / "parts.json",
            categories=master_root / "categories.json",
            manufacturers=master_root / "manufacturers.json",
            tags=master_root / "tags.json",
            locations=master_root / "locations.json",
        )


class JsonMasterDataStore:
    def __init__(self, repo_root: Path) -> None:
        self._paths = MasterDataPaths.from_root(repo_root)

    @staticmethod
    def _load_list(
        path: Path, mapper: Callable[[dict[str, Any]], T], validator: Validator
    ) -> List[T]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError(f"Expected list in {path}, got {type(payload).__name__}")
        for index, item in enumerate(payload):
            validator(item, f"{path}[{index}]")
        return [mapper(item) for item in payload]

    @staticmethod
    def _save_list(
        path: Path,
        items: Iterable[T],
        serializer: Callable[[T], dict[str, Any]],
        validator: Validator,
    ) -> None:
        payload = [serializer(item) for item in items]
        for index, item in enumerate(payload):
            validator(item, f"{path}[{index}]")
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def load_racks(self) -> List[Rack]:
        return self._load_list(self._paths.racks, Rack.from_dict, _validate_rack)

    def save_racks(self, racks: Sequence[Rack]) -> None:
        self._save_list(self._paths.racks, racks, Rack.to_dict, _validate_rack)

    def load_drawers(self) -> List[Drawer]:
        return self._load_list(self._paths.drawers, Drawer.from_dict, _validate_drawer)

    def save_drawers(self, drawers: Sequence[Drawer]) -> None:
        self._save_list(self._paths.drawers, drawers, Drawer.to_dict, _validate_drawer)

    def load_parts(self) -> List[Part]:
        return self._load_list(self._paths.parts, Part.from_dict, _validate_part)

    def save_parts(self, parts: Sequence[Part]) -> None:
        self._save_list(self._paths.parts, parts, Part.to_dict, _validate_part)

    def load_categories(self) -> List[Category]:
        return self._load_list(self._paths.categories, Category.from_dict, _validate_category)

    def save_categories(self, categories: Sequence[Category]) -> None:
        self._save_list(self._paths.categories, categories, Category.to_dict, _validate_category)

    def load_manufacturers(self) -> List[Manufacturer]:
        return self._load_list(
            self._paths.manufacturers, Manufacturer.from_dict, _validate_manufacturer
        )

    def save_manufacturers(self, manufacturers: Sequence[Manufacturer]) -> None:
        self._save_list(
            self._paths.manufacturers, manufacturers, Manufacturer.to_dict, _validate_manufacturer
        )

    def load_tags(self) -> List[Tag]:
        return self._load_list(self._paths.tags, Tag.from_dict, _validate_tag)

    def save_tags(self, tags: Sequence[Tag]) -> None:
        self._save_list(self._paths.tags, tags, Tag.to_dict, _validate_tag)

    def load_locations(self) -> List[Location]:
        return self._load_list(self._paths.locations, Location.from_dict, _validate_location)

    def save_locations(self, locations: Sequence[Location]) -> None:
        self._save_list(
            self._paths.locations, locations, Location.to_dict, _validate_location
        )


@dataclass(frozen=True)
class MovementDataPaths:
    movements_root: Path

    @classmethod
    def from_root(cls, root: Path) -> "MovementDataPaths":
        return cls(movements_root=root / "data" / "movements")

    def stock_movements(self, period: str) -> Path:
        return self.movements_root / f"stock_movements_{period}.json"

    def adjustments(self, period: str) -> Path:
        return self.movements_root / f"adjustments_{period}.json"

    def reservations(self) -> Path:
        return self.movements_root / "reservations.json"


class JsonMovementDataStore:
    def __init__(self, repo_root: Path) -> None:
        self._paths = MovementDataPaths.from_root(repo_root)

    def load_stock_movements(self, period: str) -> List[StockMovement]:
        return JsonMasterDataStore._load_list(
            self._paths.stock_movements(period), StockMovement.from_dict, _validate_stock_movement
        )

    def save_stock_movements(self, period: str, movements: Sequence[StockMovement]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.stock_movements(period),
            movements,
            StockMovement.to_dict,
            _validate_stock_movement,
        )

    def load_adjustments(self, period: str) -> List[Adjustment]:
        return JsonMasterDataStore._load_list(
            self._paths.adjustments(period), Adjustment.from_dict, _validate_adjustment
        )

    def save_adjustments(self, period: str, adjustments: Sequence[Adjustment]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.adjustments(period),
            adjustments,
            Adjustment.to_dict,
            _validate_adjustment,
        )

    def load_reservations(self) -> List[Reservation]:
        return JsonMasterDataStore._load_list(
            self._paths.reservations(), Reservation.from_dict, _validate_reservation
        )

    def save_reservations(self, reservations: Sequence[Reservation]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.reservations(), reservations, Reservation.to_dict, _validate_reservation
        )


@dataclass(frozen=True)
class IndexDataPaths:
    indexes_root: Path

    @classmethod
    def from_root(cls, root: Path) -> "IndexDataPaths":
        return cls(indexes_root=root / "data" / "indexes")

    def parts_by_tag(self) -> Path:
        return self.indexes_root / "parts_by_tag.json"

    def parts_by_category(self) -> Path:
        return self.indexes_root / "parts_by_category.json"

    def parts_by_drawer(self) -> Path:
        return self.indexes_root / "parts_by_drawer.json"


class JsonIndexDataStore:
    def __init__(self, repo_root: Path) -> None:
        self._paths = IndexDataPaths.from_root(repo_root)

    def load_parts_by_tag(self) -> List[PartsByTag]:
        return JsonMasterDataStore._load_list(
            self._paths.parts_by_tag(), PartsByTag.from_dict, _validate_parts_by_tag
        )

    def save_parts_by_tag(self, items: Sequence[PartsByTag]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.parts_by_tag(), items, PartsByTag.to_dict, _validate_parts_by_tag
        )

    def load_parts_by_category(self) -> List[PartsByCategory]:
        return JsonMasterDataStore._load_list(
            self._paths.parts_by_category(), PartsByCategory.from_dict, _validate_parts_by_category
        )

    def save_parts_by_category(self, items: Sequence[PartsByCategory]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.parts_by_category(),
            items,
            PartsByCategory.to_dict,
            _validate_parts_by_category,
        )

    def load_parts_by_drawer(self) -> List[PartsByDrawer]:
        return JsonMasterDataStore._load_list(
            self._paths.parts_by_drawer(), PartsByDrawer.from_dict, _validate_parts_by_drawer
        )

    def save_parts_by_drawer(self, items: Sequence[PartsByDrawer]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.parts_by_drawer(),
            items,
            PartsByDrawer.to_dict,
            _validate_parts_by_drawer,
        )
