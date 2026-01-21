import json
from pathlib import Path

import pytest

from backend.models import (
    Adjustment,
    Drawer,
    Part,
    PartsByCategory,
    PartsByDrawer,
    PartsByTag,
    PixelRange,
    Rack,
    Reservation,
    StockMovement,
)
from backend.storage import JsonIndexDataStore, JsonMasterDataStore, JsonMovementDataStore


@pytest.fixture()
def temp_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path
    (repo_root / "data" / "master").mkdir(parents=True)
    (repo_root / "data" / "movements").mkdir(parents=True)
    (repo_root / "data" / "indexes").mkdir(parents=True)
    return repo_root


def write_json(path: Path, payload: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_load_and_save_racks_round_trip(temp_repo_root: Path) -> None:
    racks_path = temp_repo_root / "data" / "master" / "racks.json"
    racks_payload = [
        {
            "id": "rack-1",
            "name": "Main Rack",
            "wledInstance": "wled-main",
            "rows": 2,
            "drawersPerRow": 3,
        }
    ]
    write_json(racks_path, racks_payload)

    store = JsonMasterDataStore(temp_repo_root)
    racks = store.load_racks()

    assert racks == [
        Rack(
            id="rack-1",
            name="Main Rack",
            wled_instance="wled-main",
            rows=2,
            drawers_per_row=3,
        )
    ]

    updated = [
        Rack(
            id="rack-2",
            name="Secondary",
            wled_instance="wled-secondary",
            rows=1,
            drawers_per_row=2,
        )
    ]
    store.save_racks(updated)

    saved_payload = json.loads(racks_path.read_text(encoding="utf-8"))
    assert saved_payload == [
        {
            "id": "rack-2",
            "name": "Secondary",
            "wledInstance": "wled-secondary",
            "rows": 1,
            "drawersPerRow": 2,
        }
    ]


def test_load_drawers_and_parts_with_optional_fields(temp_repo_root: Path) -> None:
    drawers_path = temp_repo_root / "data" / "master" / "drawers.json"
    parts_path = temp_repo_root / "data" / "master" / "parts.json"

    write_json(
        drawers_path,
        [
            {
                "id": "drawer-1",
                "rackId": "rack-1",
                "row": 1,
                "col": 1,
                "label": "A1",
                "pixelRange": {"start": 0, "count": 8},
            }
        ],
    )
    write_json(
        parts_path,
        [
            {
                "id": "part-1",
                "name": "Resistor 1k",
                "categoryId": "cat-1",
                "manufacturerId": "mfg-1",
                "drawerId": "drawer-1",
                "tags": ["resistor", "1k"],
                "quantity": 100,
            }
        ],
    )

    store = JsonMasterDataStore(temp_repo_root)

    drawers = store.load_drawers()
    parts = store.load_parts()

    assert drawers == [
        Drawer(
            id="drawer-1",
            rack_id="rack-1",
            row=1,
            col=1,
            label="A1",
            pixel_range=PixelRange(start=0, count=8),
        )
    ]
    assert parts == [
        Part(
            id="part-1",
            name="Resistor 1k",
            category_id="cat-1",
            manufacturer_id="mfg-1",
            drawer_id="drawer-1",
            tags=["resistor", "1k"],
            quantity=100,
            notes=None,
            images=[],
        )
    ]


def test_load_and_save_movements(temp_repo_root: Path) -> None:
    movements_store = JsonMovementDataStore(temp_repo_root)
    period = "202401"

    stock_path = temp_repo_root / "data" / "movements" / f"stock_movements_{period}.json"
    adjustments_path = temp_repo_root / "data" / "movements" / f"adjustments_{period}.json"
    reservations_path = temp_repo_root / "data" / "movements" / "reservations.json"

    write_json(
        stock_path,
        [
            {
                "id": "move-1",
                "partId": "part-1",
                "type": "in",
                "qty": 5,
                "timestamp": "2024-01-01T10:00:00Z",
            }
        ],
    )
    write_json(
        adjustments_path,
        [
            {
                "id": "adj-1",
                "partId": "part-2",
                "delta": -2,
                "timestamp": "2024-01-02T09:00:00Z",
                "reason": "Cycle count",
            }
        ],
    )
    write_json(
        reservations_path,
        [
            {
                "id": "res-1",
                "partId": "part-3",
                "qty": 3,
                "status": "active",
                "timestamp": "2024-01-03T08:00:00Z",
            }
        ],
    )

    assert movements_store.load_stock_movements(period) == [
        StockMovement(
            id="move-1",
            part_id="part-1",
            movement_type="in",
            qty=5,
            timestamp="2024-01-01T10:00:00Z",
            note=None,
        )
    ]
    assert movements_store.load_adjustments(period) == [
        Adjustment(
            id="adj-1",
            part_id="part-2",
            delta=-2,
            timestamp="2024-01-02T09:00:00Z",
            reason="Cycle count",
        )
    ]
    assert movements_store.load_reservations() == [
        Reservation(
            id="res-1",
            part_id="part-3",
            qty=3,
            status="active",
            timestamp="2024-01-03T08:00:00Z",
            note=None,
        )
    ]

    movements_store.save_stock_movements(
        period,
        [
            StockMovement(
                id="move-2",
                part_id="part-4",
                movement_type="out",
                qty=1,
                timestamp="2024-01-04T07:00:00Z",
                note="Used in build",
            )
        ],
    )
    saved_stock = json.loads(stock_path.read_text(encoding="utf-8"))
    assert saved_stock == [
        {
            "id": "move-2",
            "partId": "part-4",
            "type": "out",
            "qty": 1,
            "timestamp": "2024-01-04T07:00:00Z",
            "note": "Used in build",
        }
    ]


def test_load_and_save_indexes(temp_repo_root: Path) -> None:
    index_store = JsonIndexDataStore(temp_repo_root)
    by_tag_path = temp_repo_root / "data" / "indexes" / "parts_by_tag.json"
    by_category_path = temp_repo_root / "data" / "indexes" / "parts_by_category.json"
    by_drawer_path = temp_repo_root / "data" / "indexes" / "parts_by_drawer.json"

    write_json(by_tag_path, [{"tagId": "tag-1", "partIds": ["part-1", "part-2"]}])
    write_json(
        by_category_path,
        [{"categoryId": "cat-1", "partIds": ["part-3"]}],
    )
    write_json(by_drawer_path, [{"drawerId": "drawer-1", "partIds": ["part-4"]}])

    assert index_store.load_parts_by_tag() == [
        PartsByTag(tag_id="tag-1", part_ids=["part-1", "part-2"])
    ]
    assert index_store.load_parts_by_category() == [
        PartsByCategory(category_id="cat-1", part_ids=["part-3"])
    ]
    assert index_store.load_parts_by_drawer() == [
        PartsByDrawer(drawer_id="drawer-1", part_ids=["part-4"])
    ]

    index_store.save_parts_by_tag([PartsByTag(tag_id="tag-2", part_ids=["part-5"])])
    saved_tags = json.loads(by_tag_path.read_text(encoding="utf-8"))
    assert saved_tags == [{"tagId": "tag-2", "partIds": ["part-5"]}]
