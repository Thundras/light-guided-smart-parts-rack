from pathlib import Path

from backend.lighting import GREEN, OFF, MockWledController, PickByLightService
from backend.models import Drawer, Part, PixelRange, Rack
from backend.services import MasterDataService
from backend.storage import JsonMasterDataStore


def _build_master_service(tmp_path: Path) -> MasterDataService:
    master_dir = tmp_path / "data" / "master"
    master_dir.mkdir(parents=True)
    for name in (
        "racks",
        "drawers",
        "parts",
        "categories",
        "manufacturers",
        "tags",
        "locations",
    ):
        (master_dir / f"{name}.json").write_text("[]", encoding="utf-8")
    return MasterDataService(JsonMasterDataStore(tmp_path))


def test_highlight_parts_lights_matching_drawer_green_and_others_off(tmp_path: Path) -> None:
    service = _build_master_service(tmp_path)
    service.create_rack(
        Rack(id="rack-1", name="Main", wled_instance="wled-main", rows=1, drawers_per_row=2)
    )
    drawer_a = Drawer(
        id="drawer-a",
        rack_id="rack-1",
        row=0,
        col=0,
        label="A",
        pixel_range=PixelRange(start=0, count=5),
    )
    drawer_b = Drawer(
        id="drawer-b",
        rack_id="rack-1",
        row=0,
        col=1,
        label="B",
        pixel_range=PixelRange(start=5, count=5),
    )
    service.create_drawer(drawer_a)
    service.create_drawer(drawer_b)

    controller = MockWledController()
    pick_by_light = PickByLightService(service, controller)

    matching_part = Part(
        id="part-1",
        name="Resistor",
        category_id="cat-1",
        manufacturer_id="mfg-1",
        drawer_id="drawer-a",
        tags=[],
        quantity=10,
    )
    pick_by_light.highlight_parts([matching_part])

    assert controller.color_for("wled-main", drawer_a.pixel_range) == GREEN
    assert controller.color_for("wled-main", drawer_b.pixel_range) == OFF


def test_highlight_parts_clears_previous_highlight_on_new_search(tmp_path: Path) -> None:
    service = _build_master_service(tmp_path)
    service.create_rack(
        Rack(id="rack-1", name="Main", wled_instance="wled-main", rows=1, drawers_per_row=2)
    )
    drawer_a = Drawer(
        id="drawer-a",
        rack_id="rack-1",
        row=0,
        col=0,
        label="A",
        pixel_range=PixelRange(start=0, count=5),
    )
    drawer_b = Drawer(
        id="drawer-b",
        rack_id="rack-1",
        row=0,
        col=1,
        label="B",
        pixel_range=PixelRange(start=5, count=5),
    )
    service.create_drawer(drawer_a)
    service.create_drawer(drawer_b)

    controller = MockWledController()
    pick_by_light = PickByLightService(service, controller)

    part_a = Part(
        id="part-1",
        name="Resistor",
        category_id="cat-1",
        manufacturer_id="mfg-1",
        drawer_id="drawer-a",
        tags=[],
        quantity=10,
    )
    part_b = Part(
        id="part-2",
        name="Capacitor",
        category_id="cat-1",
        manufacturer_id="mfg-1",
        drawer_id="drawer-b",
        tags=[],
        quantity=10,
    )

    pick_by_light.highlight_parts([part_a])
    assert controller.color_for("wled-main", drawer_a.pixel_range) == GREEN

    # a new search matching only drawer B must turn drawer A back off, not just leave it lit
    pick_by_light.highlight_parts([part_b])
    assert controller.color_for("wled-main", drawer_a.pixel_range) == OFF
    assert controller.color_for("wled-main", drawer_b.pixel_range) == GREEN
