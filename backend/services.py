from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generic, List, Sequence, TypeVar

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


class CrudService(Generic[T]):
    """Generic id-keyed CRUD over a load/save pair. Used wherever an entity type has a plain
    list-of-records JSON store with a single id field — covers all seven master data entities
    identically, so each one just supplies its own load/save/key instead of repeating the CRUD
    logic."""

    def __init__(
        self,
        load: Callable[[], List[T]],
        save: Callable[[Sequence[T]], None],
        key: Callable[[T], str],
        label: str,
    ) -> None:
        self._load = load
        self._save = save
        self._key = key
        self._label = label

    def list(self) -> List[T]:
        return self._load()

    def get(self, item_id: str) -> T:
        return _get_by_id(self._load(), item_id, self._key, self._label)

    def create(self, item: T) -> None:
        items = self._load()
        _ensure_absent(items, self._key(item), self._key, self._label)
        items.append(item)
        self._save(items)

    def update(self, item: T) -> None:
        items = _replace_by_id(self._load(), item, self._key, self._label)
        self._save(items)

    def delete(self, item_id: str) -> None:
        items = _delete_by_id(self._load(), item_id, self._key, self._label)
        self._save(items)


class MasterDataService:
    def __init__(self, store: JsonMasterDataStore) -> None:
        self._store = store
        self._racks = CrudService(store.load_racks, store.save_racks, lambda x: x.id, "Rack")
        self._drawers = CrudService(
            store.load_drawers, store.save_drawers, lambda x: x.id, "Drawer"
        )
        self._parts = CrudService(store.load_parts, store.save_parts, lambda x: x.id, "Part")
        self._categories = CrudService(
            store.load_categories, store.save_categories, lambda x: x.id, "Category"
        )
        self._manufacturers = CrudService(
            store.load_manufacturers, store.save_manufacturers, lambda x: x.id, "Manufacturer"
        )
        self._tags = CrudService(store.load_tags, store.save_tags, lambda x: x.id, "Tag")
        self._locations = CrudService(
            store.load_locations, store.save_locations, lambda x: x.id, "Location"
        )

    def list_racks(self) -> List[Rack]:
        return self._racks.list()

    def get_rack(self, rack_id: str) -> Rack:
        return self._racks.get(rack_id)

    def create_rack(self, rack: Rack) -> None:
        self._racks.create(rack)

    def update_rack(self, rack: Rack) -> None:
        self._racks.update(rack)

    def delete_rack(self, rack_id: str) -> None:
        self._racks.delete(rack_id)

    def list_drawers(self) -> List[Drawer]:
        return self._drawers.list()

    def get_drawer(self, drawer_id: str) -> Drawer:
        return self._drawers.get(drawer_id)

    def create_drawer(self, drawer: Drawer) -> None:
        self._drawers.create(drawer)

    def update_drawer(self, drawer: Drawer) -> None:
        self._drawers.update(drawer)

    def delete_drawer(self, drawer_id: str) -> None:
        self._drawers.delete(drawer_id)

    def list_parts(self) -> List[Part]:
        return self._parts.list()

    def get_part(self, part_id: str) -> Part:
        return self._parts.get(part_id)

    def create_part(self, part: Part) -> None:
        self._parts.create(part)

    def update_part(self, part: Part) -> None:
        self._parts.update(part)

    def delete_part(self, part_id: str) -> None:
        self._parts.delete(part_id)

    def list_categories(self) -> List[Category]:
        return self._categories.list()

    def get_category(self, category_id: str) -> Category:
        return self._categories.get(category_id)

    def create_category(self, category: Category) -> None:
        self._categories.create(category)

    def update_category(self, category: Category) -> None:
        self._categories.update(category)

    def delete_category(self, category_id: str) -> None:
        self._categories.delete(category_id)

    def list_manufacturers(self) -> List[Manufacturer]:
        return self._manufacturers.list()

    def get_manufacturer(self, manufacturer_id: str) -> Manufacturer:
        return self._manufacturers.get(manufacturer_id)

    def create_manufacturer(self, manufacturer: Manufacturer) -> None:
        self._manufacturers.create(manufacturer)

    def update_manufacturer(self, manufacturer: Manufacturer) -> None:
        self._manufacturers.update(manufacturer)

    def delete_manufacturer(self, manufacturer_id: str) -> None:
        self._manufacturers.delete(manufacturer_id)

    def list_tags(self) -> List[Tag]:
        return self._tags.list()

    def get_tag(self, tag_id: str) -> Tag:
        return self._tags.get(tag_id)

    def create_tag(self, tag: Tag) -> None:
        self._tags.create(tag)

    def update_tag(self, tag: Tag) -> None:
        self._tags.update(tag)

    def delete_tag(self, tag_id: str) -> None:
        self._tags.delete(tag_id)

    def list_locations(self) -> List[Location]:
        return self._locations.list()

    def get_location(self, location_id: str) -> Location:
        return self._locations.get(location_id)

    def create_location(self, location: Location) -> None:
        self._locations.create(location)

    def update_location(self, location: Location) -> None:
        self._locations.update(location)

    def delete_location(self, location_id: str) -> None:
        self._locations.delete(location_id)


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
