from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable, Iterable, List, Sequence, TypeVar

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
from .schema import (
    SchemaValidationError,
    validate_adjustment,
    validate_category,
    validate_drawer,
    validate_list_payload,
    validate_location,
    validate_manufacturer,
    validate_part,
    validate_parts_by_category,
    validate_parts_by_drawer,
    validate_parts_by_tag,
    validate_rack,
    validate_reservation,
    validate_stock_movement,
    validate_tag,
)

T = TypeVar("T")


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
        path: Path,
        mapper: Callable[[dict[str, Any]], T],
        validator: Callable[[Any, str, str], None],
    ) -> List[T]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except JSONDecodeError as exc:
            raise SchemaValidationError(f"Invalid JSON in {path}: {exc.msg}") from exc
        validate_list_payload(payload, validator, str(path))
        return [mapper(item) for item in payload]

    @staticmethod
    def _save_list(
        path: Path,
        items: Iterable[T],
        serializer: Callable[[T], dict[str, Any]],
        validator: Callable[[Any, str, str], None],
    ) -> None:
        payload = [serializer(item) for item in items]
        validate_list_payload(payload, validator, str(path))
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def load_racks(self) -> List[Rack]:
        return self._load_list(self._paths.racks, Rack.from_dict, validate_rack)

    def save_racks(self, racks: Sequence[Rack]) -> None:
        self._save_list(self._paths.racks, racks, Rack.to_dict, validate_rack)

    def load_drawers(self) -> List[Drawer]:
        return self._load_list(self._paths.drawers, Drawer.from_dict, validate_drawer)

    def save_drawers(self, drawers: Sequence[Drawer]) -> None:
        self._save_list(self._paths.drawers, drawers, Drawer.to_dict, validate_drawer)

    def load_parts(self) -> List[Part]:
        return self._load_list(self._paths.parts, Part.from_dict, validate_part)

    def save_parts(self, parts: Sequence[Part]) -> None:
        self._save_list(self._paths.parts, parts, Part.to_dict, validate_part)

    def load_categories(self) -> List[Category]:
        return self._load_list(self._paths.categories, Category.from_dict, validate_category)

    def save_categories(self, categories: Sequence[Category]) -> None:
        self._save_list(self._paths.categories, categories, Category.to_dict, validate_category)

    def load_manufacturers(self) -> List[Manufacturer]:
        return self._load_list(
            self._paths.manufacturers, Manufacturer.from_dict, validate_manufacturer
        )

    def save_manufacturers(self, manufacturers: Sequence[Manufacturer]) -> None:
        self._save_list(
            self._paths.manufacturers,
            manufacturers,
            Manufacturer.to_dict,
            validate_manufacturer,
        )

    def load_tags(self) -> List[Tag]:
        return self._load_list(self._paths.tags, Tag.from_dict, validate_tag)

    def save_tags(self, tags: Sequence[Tag]) -> None:
        self._save_list(self._paths.tags, tags, Tag.to_dict, validate_tag)

    def load_locations(self) -> List[Location]:
        return self._load_list(self._paths.locations, Location.from_dict, validate_location)

    def save_locations(self, locations: Sequence[Location]) -> None:
        self._save_list(self._paths.locations, locations, Location.to_dict, validate_location)


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
            self._paths.stock_movements(period),
            StockMovement.from_dict,
            validate_stock_movement,
        )

    def save_stock_movements(self, period: str, movements: Sequence[StockMovement]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.stock_movements(period),
            movements,
            StockMovement.to_dict,
            validate_stock_movement,
        )

    def load_adjustments(self, period: str) -> List[Adjustment]:
        return JsonMasterDataStore._load_list(
            self._paths.adjustments(period), Adjustment.from_dict, validate_adjustment
        )

    def save_adjustments(self, period: str, adjustments: Sequence[Adjustment]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.adjustments(period),
            adjustments,
            Adjustment.to_dict,
            validate_adjustment,
        )

    def load_reservations(self) -> List[Reservation]:
        return JsonMasterDataStore._load_list(
            self._paths.reservations(), Reservation.from_dict, validate_reservation
        )

    def save_reservations(self, reservations: Sequence[Reservation]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.reservations(),
            reservations,
            Reservation.to_dict,
            validate_reservation,
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
            self._paths.parts_by_tag(), PartsByTag.from_dict, validate_parts_by_tag
        )

    def save_parts_by_tag(self, items: Sequence[PartsByTag]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.parts_by_tag(), items, PartsByTag.to_dict, validate_parts_by_tag
        )

    def load_parts_by_category(self) -> List[PartsByCategory]:
        return JsonMasterDataStore._load_list(
            self._paths.parts_by_category(),
            PartsByCategory.from_dict,
            validate_parts_by_category,
        )

    def save_parts_by_category(self, items: Sequence[PartsByCategory]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.parts_by_category(),
            items,
            PartsByCategory.to_dict,
            validate_parts_by_category,
        )

    def load_parts_by_drawer(self) -> List[PartsByDrawer]:
        return JsonMasterDataStore._load_list(
            self._paths.parts_by_drawer(),
            PartsByDrawer.from_dict,
            validate_parts_by_drawer,
        )

    def save_parts_by_drawer(self, items: Sequence[PartsByDrawer]) -> None:
        JsonMasterDataStore._save_list(
            self._paths.parts_by_drawer(),
            items,
            PartsByDrawer.to_dict,
            validate_parts_by_drawer,
        )
