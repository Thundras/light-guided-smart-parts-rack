import json
from pathlib import Path

from backend.models import (
    Adjustment,
    PartsByTag,
    Rack,
    Reservation,
    StockMovement,
)
from backend.services import IndexDataService, MasterDataService, MovementDataService
from backend.storage import JsonIndexDataStore, JsonMasterDataStore, JsonMovementDataStore


def write_json(path: Path, payload: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path
    (repo_root / "data" / "master").mkdir(parents=True)
    (repo_root / "data" / "movements").mkdir(parents=True)
    (repo_root / "data" / "indexes").mkdir(parents=True)
    return repo_root


def test_master_data_service_crud(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    racks_path = repo_root / "data" / "master" / "racks.json"
    write_json(racks_path, [])

    service = MasterDataService(JsonMasterDataStore(repo_root))
    rack = Rack(
        id="rack-1",
        name="Main Rack",
        wled_instance="wled-main",
        rows=2,
        drawers_per_row=3,
    )
    service.create_rack(rack)

    saved_payload = json.loads(racks_path.read_text(encoding="utf-8"))
    assert saved_payload == [
        {
            "id": "rack-1",
            "name": "Main Rack",
            "wledInstance": "wled-main",
            "rows": 2,
            "drawersPerRow": 3,
        }
    ]

    updated = Rack(
        id="rack-1",
        name="Updated",
        wled_instance="wled-main",
        rows=3,
        drawers_per_row=4,
    )
    service.update_rack(updated)
    assert service.get_rack("rack-1").name == "Updated"

    service.delete_rack("rack-1")
    assert json.loads(racks_path.read_text(encoding="utf-8")) == []


def test_movement_data_service_crud(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    period = "202401"
    stock_path = repo_root / "data" / "movements" / f"stock_movements_{period}.json"
    adjustments_path = repo_root / "data" / "movements" / f"adjustments_{period}.json"
    reservations_path = repo_root / "data" / "movements" / "reservations.json"
    write_json(stock_path, [])
    write_json(adjustments_path, [])
    write_json(reservations_path, [])

    service = MovementDataService(JsonMovementDataStore(repo_root))
    movement = StockMovement(
        id="move-1",
        part_id="part-1",
        movement_type="in",
        qty=5,
        timestamp="2024-01-01T10:00:00Z",
    )
    service.create_stock_movement(period, movement)
    assert service.get_stock_movement(period, "move-1").qty == 5

    updated = StockMovement(
        id="move-1",
        part_id="part-1",
        movement_type="in",
        qty=7,
        timestamp="2024-01-01T10:00:00Z",
        note="Correction",
    )
    service.update_stock_movement(period, updated)
    assert service.get_stock_movement(period, "move-1").qty == 7

    adjustment = Adjustment(
        id="adj-1",
        part_id="part-2",
        delta=-1,
        timestamp="2024-01-02T09:00:00Z",
        reason="Audit",
    )
    service.create_adjustment(period, adjustment)
    assert service.get_adjustment(period, "adj-1").reason == "Audit"

    reservation = Reservation(
        id="res-1",
        part_id="part-3",
        qty=2,
        status="active",
        timestamp="2024-01-03T08:00:00Z",
    )
    service.create_reservation(reservation)
    assert service.get_reservation("res-1").qty == 2

    service.delete_stock_movement(period, "move-1")
    assert json.loads(stock_path.read_text(encoding="utf-8")) == []


def test_index_data_service_crud(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    by_tag_path = repo_root / "data" / "indexes" / "parts_by_tag.json"
    write_json(by_tag_path, [])

    service = IndexDataService(JsonIndexDataStore(repo_root))
    entry = PartsByTag(tag_id="tag-1", part_ids=["part-1", "part-2"])
    service.create_parts_by_tag(entry)

    saved_payload = json.loads(by_tag_path.read_text(encoding="utf-8"))
    assert saved_payload == [{"tagId": "tag-1", "partIds": ["part-1", "part-2"]}]

    updated = PartsByTag(tag_id="tag-1", part_ids=["part-3"])
    service.update_parts_by_tag(updated)
    assert service.get_parts_by_tag("tag-1").part_ids == ["part-3"]

    service.delete_parts_by_tag("tag-1")
    assert json.loads(by_tag_path.read_text(encoding="utf-8")) == []
