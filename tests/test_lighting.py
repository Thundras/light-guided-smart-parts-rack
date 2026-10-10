import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest

from backend.lighting import (
    GREEN,
    OFF,
    DispatchingWledController,
    HttpWledController,
    MockWledController,
    PickByLightService,
    WledConnectionError,
)
from backend.models import Drawer, Part, PixelRange, Rack, WledDevice
from backend.services import MasterDataService
from backend.storage import JsonMasterDataStore


def _build_master_service(tmp_path: Path) -> MasterDataService:
    master_dir = tmp_path / "data" / "master"
    master_dir.mkdir(parents=True)
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
        (master_dir / f"{name}.json").write_text("[]", encoding="utf-8")
    return MasterDataService(JsonMasterDataStore(tmp_path))


def test_highlight_parts_lights_matching_drawer_green_and_others_off(tmp_path: Path) -> None:
    service = _build_master_service(tmp_path)
    service.create_rack(
        Rack(id="rack-1", name="Main", wled_instance="wled-main", row_layout=[2])
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
        Rack(id="rack-1", name="Main", wled_instance="wled-main", row_layout=[2])
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


class _FakeWledHandler(BaseHTTPRequestHandler):
    """Stands in for a real WLED device's HTTP API: records every POST /json/state body it
    receives, in request order, on the class itself (shared across requests to the same server).
    """

    received: List[Dict[str, Any]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        type(self).received.append(json.loads(body))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture()
def fake_wled_server() -> Iterator[str]:
    _FakeWledHandler.received = []
    server = HTTPServer(("127.0.0.1", 0), _FakeWledHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()


def test_http_wled_controller_posts_expected_segment_shape(fake_wled_server: str) -> None:
    controller = HttpWledController()
    controller.set_pixels(fake_wled_server, PixelRange(start=5, count=10), (0, 255, 0))

    assert _FakeWledHandler.received == [
        {"seg": [{"start": 5, "stop": 15, "col": [[0, 255, 0]], "fx": 0}]}
    ]


def test_http_wled_controller_raises_connection_error_for_unreachable_host() -> None:
    controller = HttpWledController(timeout=0.2)

    with pytest.raises(WledConnectionError):
        # port 1 is reserved and never accepts connections -- reliably "unreachable" without
        # depending on any real network state
        controller.set_pixels("127.0.0.1:1", PixelRange(start=0, count=1), GREEN)


def test_dispatching_controller_only_calls_hardware_when_device_is_connected(
    tmp_path: Path,
) -> None:
    service = _build_master_service(tmp_path)
    service.create_wled_device(
        WledDevice(id="wled-sim-only", host="127.0.0.1:1", hardware_connected=False)
    )
    service.create_wled_device(
        WledDevice(id="wled-live", host="127.0.0.1:1", hardware_connected=True)
    )

    simulated = MockWledController()
    hardware_calls: List[str] = []

    class RecordingHardware:
        def set_pixels(self, host, pixel_range, color):  # noqa: ANN001 - test double
            hardware_calls.append(host)

    dispatcher = DispatchingWledController(service, simulated, RecordingHardware())

    pixel_range = PixelRange(start=0, count=5)
    dispatcher.set_pixels("wled-sim-only", pixel_range, GREEN)
    dispatcher.set_pixels("wled-live", pixel_range, GREEN)
    dispatcher.set_pixels("wled-unknown", pixel_range, GREEN)  # no device record at all

    # simulated state is always updated, regardless of hardware_connected
    assert simulated.color_for("wled-sim-only", pixel_range) == GREEN
    assert simulated.color_for("wled-live", pixel_range) == GREEN
    assert simulated.color_for("wled-unknown", pixel_range) == GREEN

    # only the connected device's host was actually dispatched to hardware
    assert hardware_calls == ["127.0.0.1:1"]


def test_dispatching_controller_isolates_hardware_errors(tmp_path: Path) -> None:
    service = _build_master_service(tmp_path)
    service.create_wled_device(
        WledDevice(id="wled-live", host="127.0.0.1:1", hardware_connected=True)
    )

    simulated = MockWledController()
    errors: List[tuple] = []

    class FailingHardware:
        def set_pixels(self, host, pixel_range, color):  # noqa: ANN001 - test double
            raise WledConnectionError("device offline")

    dispatcher = DispatchingWledController(
        service,
        simulated,
        FailingHardware(),
        on_hardware_error=lambda instance, exc: errors.append((instance, str(exc))),
    )

    pixel_range = PixelRange(start=0, count=5)
    # must not raise -- a dead ESP32 shouldn't break the whole pick-by-light call
    dispatcher.set_pixels("wled-live", pixel_range, GREEN)

    assert simulated.color_for("wled-live", pixel_range) == GREEN
    assert errors == [("wled-live", "device offline")]
