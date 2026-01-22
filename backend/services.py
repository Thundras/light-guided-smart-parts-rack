from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Sequence, TypeVar

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
from .storage import JsonIndexDataStore, JsonMasterDataStore, JsonMovementDataStore

T = TypeVar("T")


def _get_by_id(items: Sequence[T], item_id: str, key: Callable[[T], str], label: str) -> T:
    for item in items:
        if key(item) == item_id:
            return item
    raise ValueError(f"{label} with id '{item_id}' not found")


def _ensure_absent(items: Sequence[T], item_id: str, key: Callable[[T], str], label: str) -> None:
    for item in items:
        if key(item) == item_id:
            raise ValueError(f"{label} with id '{item_id}' already exists")


def _replace_by_id(
    items: Sequence[T], updated: T, key: Callable[[T], str], label: str
) -> List[T]:
    updated_id = key(updated)
    replaced = False
    result: List[T] = []
    for item in items:
        if key(item) == updated_id:
            result.append(updated)
            replaced = True
        else:
            result.append(item)
    if not replaced:
        raise ValueError(f"{label} with id '{updated_id}' not found")
    return result


def _delete_by_id(items: Sequence[T], item_id: str, key: Callable[[T], str], label: str) -> List[T]:
    removed = False
    result: List[T] = []
    for item in items:
        if key(item) == item_id:
            removed = True
        else:
            result.append(item)
    if not removed:
        raise ValueError(f"{label} with id '{item_id}' not found")
    return result


class MasterDataService:
    def __init__(self, store: JsonMasterDataStore) -> None:
        self._store = store

    def list_racks(self) -> List[Rack]:
        return self._store.load_racks()

    def get_rack(self, rack_id: str) -> Rack:
        return _get_by_id(self._store.load_racks(), rack_id, lambda rack: rack.id, "Rack")

    def create_rack(self, rack: Rack) -> None:
        racks = self._store.load_racks()
        _ensure_absent(racks, rack.id, lambda item: item.id, "Rack")
        racks.append(rack)
        self._store.save_racks(racks)

    def update_rack(self, rack: Rack) -> None:
        racks = _replace_by_id(self._store.load_racks(), rack, lambda item: item.id, "Rack")
        self._store.save_racks(racks)

    def delete_rack(self, rack_id: str) -> None:
        racks = _delete_by_id(self._store.load_racks(), rack_id, lambda item: item.id, "Rack")
        self._store.save_racks(racks)

    def list_drawers(self) -> List[Drawer]:
        return self._store.load_drawers()

    def get_drawer(self, drawer_id: str) -> Drawer:
        return _get_by_id(
            self._store.load_drawers(), drawer_id, lambda drawer: drawer.id, "Drawer"
        )

    def create_drawer(self, drawer: Drawer) -> None:
        drawers = self._store.load_drawers()
        _ensure_absent(drawers, drawer.id, lambda item: item.id, "Drawer")
        drawers.append(drawer)
        self._store.save_drawers(drawers)

    def update_drawer(self, drawer: Drawer) -> None:
        drawers = _replace_by_id(
            self._store.load_drawers(), drawer, lambda item: item.id, "Drawer"
        )
        self._store.save_drawers(drawers)

    def delete_drawer(self, drawer_id: str) -> None:
        drawers = _delete_by_id(
            self._store.load_drawers(), drawer_id, lambda item: item.id, "Drawer"
        )
        self._store.save_drawers(drawers)

    def list_parts(self) -> List[Part]:
        return self._store.load_parts()

    def get_part(self, part_id: str) -> Part:
        return _get_by_id(self._store.load_parts(), part_id, lambda part: part.id, "Part")

    def create_part(self, part: Part) -> None:
        parts = self._store.load_parts()
        _ensure_absent(parts, part.id, lambda item: item.id, "Part")
        parts.append(part)
        self._store.save_parts(parts)

    def update_part(self, part: Part) -> None:
        parts = _replace_by_id(self._store.load_parts(), part, lambda item: item.id, "Part")
        self._store.save_parts(parts)

    def delete_part(self, part_id: str) -> None:
        parts = _delete_by_id(self._store.load_parts(), part_id, lambda item: item.id, "Part")
        self._store.save_parts(parts)

    def list_categories(self) -> List[Category]:
        return self._store.load_categories()

    def get_category(self, category_id: str) -> Category:
        return _get_by_id(
            self._store.load_categories(), category_id, lambda item: item.id, "Category"
        )

    def create_category(self, category: Category) -> None:
        categories = self._store.load_categories()
        _ensure_absent(categories, category.id, lambda item: item.id, "Category")
        categories.append(category)
        self._store.save_categories(categories)

    def update_category(self, category: Category) -> None:
        categories = _replace_by_id(
            self._store.load_categories(), category, lambda item: item.id, "Category"
        )
        self._store.save_categories(categories)

    def delete_category(self, category_id: str) -> None:
        categories = _delete_by_id(
            self._store.load_categories(), category_id, lambda item: item.id, "Category"
        )
        self._store.save_categories(categories)

    def list_manufacturers(self) -> List[Manufacturer]:
        return self._store.load_manufacturers()

    def get_manufacturer(self, manufacturer_id: str) -> Manufacturer:
        return _get_by_id(
            self._store.load_manufacturers(), manufacturer_id, lambda item: item.id, "Manufacturer"
        )

    def create_manufacturer(self, manufacturer: Manufacturer) -> None:
        manufacturers = self._store.load_manufacturers()
        _ensure_absent(manufacturers, manufacturer.id, lambda item: item.id, "Manufacturer")
        manufacturers.append(manufacturer)
        self._store.save_manufacturers(manufacturers)

    def update_manufacturer(self, manufacturer: Manufacturer) -> None:
        manufacturers = _replace_by_id(
            self._store.load_manufacturers(),
            manufacturer,
            lambda item: item.id,
            "Manufacturer",
        )
        self._store.save_manufacturers(manufacturers)

    def delete_manufacturer(self, manufacturer_id: str) -> None:
        manufacturers = _delete_by_id(
            self._store.load_manufacturers(),
            manufacturer_id,
            lambda item: item.id,
            "Manufacturer",
        )
        self._store.save_manufacturers(manufacturers)

    def list_tags(self) -> List[Tag]:
        return self._store.load_tags()

    def get_tag(self, tag_id: str) -> Tag:
        return _get_by_id(self._store.load_tags(), tag_id, lambda item: item.id, "Tag")

    def create_tag(self, tag: Tag) -> None:
        tags = self._store.load_tags()
        _ensure_absent(tags, tag.id, lambda item: item.id, "Tag")
        tags.append(tag)
        self._store.save_tags(tags)

    def update_tag(self, tag: Tag) -> None:
        tags = _replace_by_id(self._store.load_tags(), tag, lambda item: item.id, "Tag")
        self._store.save_tags(tags)

    def delete_tag(self, tag_id: str) -> None:
        tags = _delete_by_id(self._store.load_tags(), tag_id, lambda item: item.id, "Tag")
        self._store.save_tags(tags)

    def list_locations(self) -> List[Location]:
        return self._store.load_locations()

    def get_location(self, location_id: str) -> Location:
        return _get_by_id(
            self._store.load_locations(), location_id, lambda item: item.id, "Location"
        )

    def create_location(self, location: Location) -> None:
        locations = self._store.load_locations()
        _ensure_absent(locations, location.id, lambda item: item.id, "Location")
        locations.append(location)
        self._store.save_locations(locations)

    def update_location(self, location: Location) -> None:
        locations = _replace_by_id(
            self._store.load_locations(), location, lambda item: item.id, "Location"
        )
        self._store.save_locations(locations)

    def delete_location(self, location_id: str) -> None:
        locations = _delete_by_id(
            self._store.load_locations(), location_id, lambda item: item.id, "Location"
        )
        self._store.save_locations(locations)


class MovementDataService:
    def __init__(self, store: JsonMovementDataStore) -> None:
        self._store = store

    def list_stock_movements(self, period: str) -> List[StockMovement]:
        return self._store.load_stock_movements(period)

    def get_stock_movement(self, period: str, movement_id: str) -> StockMovement:
        return _get_by_id(
            self._store.load_stock_movements(period),
            movement_id,
            lambda item: item.id,
            "Stock movement",
        )

    def create_stock_movement(self, period: str, movement: StockMovement) -> None:
        movements = self._store.load_stock_movements(period)
        _ensure_absent(movements, movement.id, lambda item: item.id, "Stock movement")
        movements.append(movement)
        self._store.save_stock_movements(period, movements)

    def update_stock_movement(self, period: str, movement: StockMovement) -> None:
        movements = _replace_by_id(
            self._store.load_stock_movements(period),
            movement,
            lambda item: item.id,
            "Stock movement",
        )
        self._store.save_stock_movements(period, movements)

    def delete_stock_movement(self, period: str, movement_id: str) -> None:
        movements = _delete_by_id(
            self._store.load_stock_movements(period),
            movement_id,
            lambda item: item.id,
            "Stock movement",
        )
        self._store.save_stock_movements(period, movements)

    def list_adjustments(self, period: str) -> List[Adjustment]:
        return self._store.load_adjustments(period)

    def get_adjustment(self, period: str, adjustment_id: str) -> Adjustment:
        return _get_by_id(
            self._store.load_adjustments(period),
            adjustment_id,
            lambda item: item.id,
            "Adjustment",
        )

    def create_adjustment(self, period: str, adjustment: Adjustment) -> None:
        adjustments = self._store.load_adjustments(period)
        _ensure_absent(adjustments, adjustment.id, lambda item: item.id, "Adjustment")
        adjustments.append(adjustment)
        self._store.save_adjustments(period, adjustments)

    def update_adjustment(self, period: str, adjustment: Adjustment) -> None:
        adjustments = _replace_by_id(
            self._store.load_adjustments(period),
            adjustment,
            lambda item: item.id,
            "Adjustment",
        )
        self._store.save_adjustments(period, adjustments)

    def delete_adjustment(self, period: str, adjustment_id: str) -> None:
        adjustments = _delete_by_id(
            self._store.load_adjustments(period),
            adjustment_id,
            lambda item: item.id,
            "Adjustment",
        )
        self._store.save_adjustments(period, adjustments)

    def list_reservations(self) -> List[Reservation]:
        return self._store.load_reservations()

    def get_reservation(self, reservation_id: str) -> Reservation:
        return _get_by_id(
            self._store.load_reservations(), reservation_id, lambda item: item.id, "Reservation"
        )

    def create_reservation(self, reservation: Reservation) -> None:
        reservations = self._store.load_reservations()
        _ensure_absent(reservations, reservation.id, lambda item: item.id, "Reservation")
        reservations.append(reservation)
        self._store.save_reservations(reservations)

    def update_reservation(self, reservation: Reservation) -> None:
        reservations = _replace_by_id(
            self._store.load_reservations(),
            reservation,
            lambda item: item.id,
            "Reservation",
        )
        self._store.save_reservations(reservations)

    def delete_reservation(self, reservation_id: str) -> None:
        reservations = _delete_by_id(
            self._store.load_reservations(),
            reservation_id,
            lambda item: item.id,
            "Reservation",
        )
        self._store.save_reservations(reservations)


class IndexDataService:
    def __init__(self, store: JsonIndexDataStore) -> None:
        self._store = store

    def list_parts_by_tag(self) -> List[PartsByTag]:
        return self._store.load_parts_by_tag()

    def get_parts_by_tag(self, tag_id: str) -> PartsByTag:
        return _get_by_id(
            self._store.load_parts_by_tag(), tag_id, lambda item: item.tag_id, "Parts by tag"
        )

    def create_parts_by_tag(self, entry: PartsByTag) -> None:
        entries = self._store.load_parts_by_tag()
        _ensure_absent(entries, entry.tag_id, lambda item: item.tag_id, "Parts by tag")
        entries.append(entry)
        self._store.save_parts_by_tag(entries)

    def update_parts_by_tag(self, entry: PartsByTag) -> None:
        entries = _replace_by_id(
            self._store.load_parts_by_tag(),
            entry,
            lambda item: item.tag_id,
            "Parts by tag",
        )
        self._store.save_parts_by_tag(entries)

    def delete_parts_by_tag(self, tag_id: str) -> None:
        entries = _delete_by_id(
            self._store.load_parts_by_tag(),
            tag_id,
            lambda item: item.tag_id,
            "Parts by tag",
        )
        self._store.save_parts_by_tag(entries)

    def list_parts_by_category(self) -> List[PartsByCategory]:
        return self._store.load_parts_by_category()

    def get_parts_by_category(self, category_id: str) -> PartsByCategory:
        return _get_by_id(
            self._store.load_parts_by_category(),
            category_id,
            lambda item: item.category_id,
            "Parts by category",
        )

    def create_parts_by_category(self, entry: PartsByCategory) -> None:
        entries = self._store.load_parts_by_category()
        _ensure_absent(
            entries, entry.category_id, lambda item: item.category_id, "Parts by category"
        )
        entries.append(entry)
        self._store.save_parts_by_category(entries)

    def update_parts_by_category(self, entry: PartsByCategory) -> None:
        entries = _replace_by_id(
            self._store.load_parts_by_category(),
            entry,
            lambda item: item.category_id,
            "Parts by category",
        )
        self._store.save_parts_by_category(entries)

    def delete_parts_by_category(self, category_id: str) -> None:
        entries = _delete_by_id(
            self._store.load_parts_by_category(),
            category_id,
            lambda item: item.category_id,
            "Parts by category",
        )
        self._store.save_parts_by_category(entries)

    def list_parts_by_drawer(self) -> List[PartsByDrawer]:
        return self._store.load_parts_by_drawer()

    def get_parts_by_drawer(self, drawer_id: str) -> PartsByDrawer:
        return _get_by_id(
            self._store.load_parts_by_drawer(),
            drawer_id,
            lambda item: item.drawer_id,
            "Parts by drawer",
        )

    def create_parts_by_drawer(self, entry: PartsByDrawer) -> None:
        entries = self._store.load_parts_by_drawer()
        _ensure_absent(entries, entry.drawer_id, lambda item: item.drawer_id, "Parts by drawer")
        entries.append(entry)
        self._store.save_parts_by_drawer(entries)

    def update_parts_by_drawer(self, entry: PartsByDrawer) -> None:
        entries = _replace_by_id(
            self._store.load_parts_by_drawer(),
            entry,
            lambda item: item.drawer_id,
            "Parts by drawer",
        )
        self._store.save_parts_by_drawer(entries)

    def delete_parts_by_drawer(self, drawer_id: str) -> None:
        entries = _delete_by_id(
            self._store.load_parts_by_drawer(),
            drawer_id,
            lambda item: item.drawer_id,
            "Parts by drawer",
        )
        self._store.save_parts_by_drawer(entries)


@dataclass(frozen=True)
class PartSearchCriteria:
    query: str | None = None
    category_id: str | None = None
    manufacturer_id: str | None = None
    drawer_id: str | None = None
    tags_any: Sequence[str] = field(default_factory=tuple)
    tags_all: Sequence[str] = field(default_factory=tuple)
    min_quantity: int | None = None
    max_quantity: int | None = None


class PartSearchService:
    def __init__(self, store: JsonMasterDataStore) -> None:
        self._store = store

    def search_parts(self, criteria: PartSearchCriteria) -> List[Part]:
        parts = self._store.load_parts()
        return [part for part in parts if _matches_criteria(part, criteria)]


def _matches_criteria(part: Part, criteria: PartSearchCriteria) -> bool:
    if criteria.category_id and part.category_id != criteria.category_id:
        return False
    if criteria.manufacturer_id and part.manufacturer_id != criteria.manufacturer_id:
        return False
    if criteria.drawer_id and part.drawer_id != criteria.drawer_id:
        return False
    if criteria.min_quantity is not None and part.quantity < criteria.min_quantity:
        return False
    if criteria.max_quantity is not None and part.quantity > criteria.max_quantity:
        return False
    if criteria.tags_any:
        if not set(criteria.tags_any).intersection(part.tags):
            return False
    if criteria.tags_all:
        if not set(criteria.tags_all).issubset(part.tags):
            return False
    if criteria.query:
        query = criteria.query.casefold()
        haystack = [
            part.id,
            part.name,
            part.notes or "",
            " ".join(part.tags),
        ]
        if not any(query in text.casefold() for text in haystack):
            return False
    return True
