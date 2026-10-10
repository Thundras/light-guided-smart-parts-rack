import json
from pathlib import Path

from backend.models import (
    Adjustment,
    Drawer,
    PartsByTag,
    PixelRange,
    Rack,
    Reservation,
    StockMovement,
    WledDevice,
)
import pytest

from backend.services import (
    ImportValidationError,
    IndexDataService,
    MasterDataService,
    MovementDataService,
)
from backend.storage import JsonIndexDataStore, JsonMasterDataStore, JsonMovementDataStore


def write_json(path: Path, payload: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path
    (repo_root / "data" / "master").mkdir(parents=True)
    (repo_root / "data" / "movements").mkdir(parents=True)
    (repo_root / "data" / "indexes").mkdir(parents=True)
    return repo_root


def test_master_data_service_wled_device_crud(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    devices_path = repo_root / "data" / "master" / "wled_devices.json"
    write_json(devices_path, [])

    service = MasterDataService(JsonMasterDataStore(repo_root))
    device = WledDevice(id="wled-main", host="192.168.1.50", hardware_connected=False)
    service.create_wled_device(device)

    assert json.loads(devices_path.read_text(encoding="utf-8")) == [
        {"id": "wled-main", "host": "192.168.1.50", "hardwareConnected": False}
    ]

    service.update_wled_device(
        WledDevice(id="wled-main", host="192.168.1.51", hardware_connected=True)
    )
    updated = service.get_wled_device("wled-main")
    assert updated.host == "192.168.1.51"
    assert updated.hardware_connected is True

    service.delete_wled_device("wled-main")
    assert service.list_wled_devices() == []


def test_master_data_service_crud(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    racks_path = repo_root / "data" / "master" / "racks.json"
    write_json(racks_path, [])

    service = MasterDataService(JsonMasterDataStore(repo_root))
    rack = Rack(
        id="rack-1",
        name="Main Rack",
        wled_instance="wled-main",
        row_layout=[2, 3],
    )
    service.create_rack(rack)

    saved_payload = json.loads(racks_path.read_text(encoding="utf-8"))
    assert saved_payload == [
        {
            "id": "rack-1",
            "name": "Main Rack",
            "wledInstance": "wled-main",
            "rowLayout": [2, 3],
        }
    ]

    updated = Rack(
        id="rack-1",
        name="Updated",
        wled_instance="wled-main",
        row_layout=[3, 4],
    )
    service.update_rack(updated)
    assert service.get_rack("rack-1").name == "Updated"

    service.delete_rack("rack-1")
    assert json.loads(racks_path.read_text(encoding="utf-8")) == []


def test_sync_drawers_for_rack_creates_missing_cells_with_sequential_pixels(
    tmp_path: Path,
) -> None:
    repo_root = build_repo_root(tmp_path)
    write_json(repo_root / "data" / "master" / "racks.json", [])
    write_json(repo_root / "data" / "master" / "drawers.json", [])

    service = MasterDataService(JsonMasterDataStore(repo_root))
    rack = Rack(id="rack-1", name="Main Rack", wled_instance="wled-main", row_layout=[2, 1])
    service.create_rack(rack)

    created = service.sync_drawers_for_rack(rack)
    assert created == 3

    drawers = sorted(service.list_drawers(), key=lambda d: (d.row, d.col))
    assert [(d.row, d.col, d.pixel_range.start, d.pixel_range.count) for d in drawers] == [
        (0, 0, 0, 1),
        (0, 1, 1, 1),
        (1, 0, 2, 1),
    ]


def test_sync_drawers_for_rack_leaves_existing_drawers_untouched(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    write_json(repo_root / "data" / "master" / "racks.json", [])
    write_json(repo_root / "data" / "master" / "drawers.json", [])

    service = MasterDataService(JsonMasterDataStore(repo_root))
    rack = Rack(id="rack-1", name="Main Rack", wled_instance="wled-main", row_layout=[2])
    service.create_rack(rack)
    service.sync_drawers_for_rack(rack)

    # user edits one drawer's label and pixel range after the fact
    edited = Drawer(
        id="rack-1-r0c0",
        rack_id="rack-1",
        row=0,
        col=0,
        label="Resistors",
        pixel_range=PixelRange(start=10, count=5),
    )
    service.update_drawer(edited)

    grown = Rack(id="rack-1", name="Main Rack", wled_instance="wled-main", row_layout=[2, 3])
    service.update_rack(grown)
    created = service.sync_drawers_for_rack(grown)

    assert created == 3
    drawers = {d.id: d for d in service.list_drawers()}
    assert drawers["rack-1-r0c0"] == edited
    assert drawers["rack-1-r0c1"].pixel_range.start == 1  # untouched, not part of the growth
    new_pixel_starts = sorted(
        d.pixel_range.start for d in drawers.values() if d.id not in ("rack-1-r0c0", "rack-1-r0c1")
    )
    assert new_pixel_starts == [15, 16, 17]


def test_master_data_export_import_round_trip(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    racks_path = repo_root / "data" / "master" / "racks.json"
    categories_path = repo_root / "data" / "master" / "categories.json"
    for name in (
        "wled_devices",
        "racks",
        "drawers",
        "parts",
        "categories",
        "manufacturers",
        "tags",
        "locations",
    ):
        write_json(repo_root / "data" / "master" / f"{name}.json", [])

    service = MasterDataService(JsonMasterDataStore(repo_root))
    service.create_rack(
        Rack(id="rack-1", name="Main Rack", wled_instance="wled-main", row_layout=[2, 3])
    )

    exported = service.export_all()
    assert exported["racks"] == [
        {
            "id": "rack-1",
            "name": "Main Rack",
            "wledInstance": "wled-main",
            "rowLayout": [2, 3],
        }
    ]
    assert exported["categories"] == []

    # Re-import: racks replaced with a different record, categories untouched (not in payload).
    service.import_all(
        {
            "racks": [
                {
                    "id": "rack-2",
                    "name": "Second Rack",
                    "wledInstance": "wled-second",
                    "rowLayout": [1],
                }
            ]
        }
    )

    assert [r.id for r in service.list_racks()] == ["rack-2"]
    assert json.loads(racks_path.read_text(encoding="utf-8")) == [
        {
            "id": "rack-2",
            "name": "Second Rack",
            "wledInstance": "wled-second",
            "rowLayout": [1],
        }
    ]
    # categories.json untouched since "categories" wasn't in the import payload.
    assert json.loads(categories_path.read_text(encoding="utf-8")) == []


def test_master_data_import_rejects_invalid_payload_without_writing(tmp_path: Path) -> None:
    repo_root = build_repo_root(tmp_path)
    racks_path = repo_root / "data" / "master" / "racks.json"
    write_json(racks_path, [])
    write_json(repo_root / "data" / "master" / "categories.json", [])

    service = MasterDataService(JsonMasterDataStore(repo_root))

    with pytest.raises(ImportValidationError) as exc_info:
        service.import_all(
            {
                "racks": [{"id": "rack-1"}],  # missing required fields
                "categories": "not-a-list",
            }
        )

    assert "racks[0]" in str(exc_info.value)
    assert "categories" in str(exc_info.value)
    # Nothing written: racks.json still empty, invalid "categories" key never touched the file.
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
