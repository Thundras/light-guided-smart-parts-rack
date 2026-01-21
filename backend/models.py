from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PixelRange:
    start: int
    count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PixelRange":
        return cls(start=int(data["start"]), count=int(data["count"]))

    def to_dict(self) -> Dict[str, Any]:
        return {"start": self.start, "count": self.count}


@dataclass(frozen=True)
class Rack:
    id: str
    name: str
    wled_instance: str
    rows: int
    drawers_per_row: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rack":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            wled_instance=str(data["wledInstance"]),
            rows=int(data["rows"]),
            drawers_per_row=int(data["drawersPerRow"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "wledInstance": self.wled_instance,
            "rows": self.rows,
            "drawersPerRow": self.drawers_per_row,
        }


@dataclass(frozen=True)
class Drawer:
    id: str
    rack_id: str
    row: int
    col: int
    label: str
    pixel_range: PixelRange

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Drawer":
        return cls(
            id=str(data["id"]),
            rack_id=str(data["rackId"]),
            row=int(data["row"]),
            col=int(data["col"]),
            label=str(data["label"]),
            pixel_range=PixelRange.from_dict(data["pixelRange"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rackId": self.rack_id,
            "row": self.row,
            "col": self.col,
            "label": self.label,
            "pixelRange": self.pixel_range.to_dict(),
        }


@dataclass(frozen=True)
class Part:
    id: str
    name: str
    category_id: str
    manufacturer_id: str
    drawer_id: str
    tags: List[str]
    quantity: int
    notes: Optional[str] = None
    images: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Part":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category_id=str(data["categoryId"]),
            manufacturer_id=str(data["manufacturerId"]),
            drawer_id=str(data["drawerId"]),
            tags=[str(tag) for tag in data.get("tags", [])],
            quantity=int(data["quantity"]),
            notes=data.get("notes"),
            images=[str(image) for image in data.get("images", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "categoryId": self.category_id,
            "manufacturerId": self.manufacturer_id,
            "drawerId": self.drawer_id,
            "tags": list(self.tags),
            "quantity": self.quantity,
        }
        if self.notes is not None:
            payload["notes"] = self.notes
        if self.images:
            payload["images"] = list(self.images)
        return payload


@dataclass(frozen=True)
class Category:
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        return cls(id=str(data["id"]), name=str(data["name"]))

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}


@dataclass(frozen=True)
class Manufacturer:
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manufacturer":
        return cls(id=str(data["id"]), name=str(data["name"]))

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}


@dataclass(frozen=True)
class Tag:
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tag":
        return cls(id=str(data["id"]), name=str(data["name"]))

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=data.get("description"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"id": self.id, "name": self.name}
        if self.description is not None:
            payload["description"] = self.description
        return payload


@dataclass(frozen=True)
class StockMovement:
    id: str
    part_id: str
    movement_type: str
    qty: int
    timestamp: str
    note: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockMovement":
        return cls(
            id=str(data["id"]),
            part_id=str(data["partId"]),
            movement_type=str(data["type"]),
            qty=int(data["qty"]),
            timestamp=str(data["timestamp"]),
            note=data.get("note"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "partId": self.part_id,
            "type": self.movement_type,
            "qty": self.qty,
            "timestamp": self.timestamp,
        }
        if self.note is not None:
            payload["note"] = self.note
        return payload


@dataclass(frozen=True)
class Adjustment:
    id: str
    part_id: str
    delta: int
    timestamp: str
    reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Adjustment":
        return cls(
            id=str(data["id"]),
            part_id=str(data["partId"]),
            delta=int(data["delta"]),
            timestamp=str(data["timestamp"]),
            reason=data.get("reason"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "partId": self.part_id,
            "delta": self.delta,
            "timestamp": self.timestamp,
        }
        if self.reason is not None:
            payload["reason"] = self.reason
        return payload


@dataclass(frozen=True)
class Reservation:
    id: str
    part_id: str
    qty: int
    status: str
    timestamp: str
    note: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reservation":
        return cls(
            id=str(data["id"]),
            part_id=str(data["partId"]),
            qty=int(data["qty"]),
            status=str(data["status"]),
            timestamp=str(data["timestamp"]),
            note=data.get("note"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": self.id,
            "partId": self.part_id,
            "qty": self.qty,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        if self.note is not None:
            payload["note"] = self.note
        return payload


@dataclass(frozen=True)
class PartsByTag:
    tag_id: str
    part_ids: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PartsByTag":
        return cls(
            tag_id=str(data["tagId"]),
            part_ids=[str(item) for item in data.get("partIds", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"tagId": self.tag_id, "partIds": list(self.part_ids)}


@dataclass(frozen=True)
class PartsByCategory:
    category_id: str
    part_ids: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PartsByCategory":
        return cls(
            category_id=str(data["categoryId"]),
            part_ids=[str(item) for item in data.get("partIds", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"categoryId": self.category_id, "partIds": list(self.part_ids)}


@dataclass(frozen=True)
class PartsByDrawer:
    drawer_id: str
    part_ids: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PartsByDrawer":
        return cls(
            drawer_id=str(data["drawerId"]),
            part_ids=[str(item) for item in data.get("partIds", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"drawerId": self.drawer_id, "partIds": list(self.part_ids)}
