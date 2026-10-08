import json
import threading
import urllib.parse
import urllib.request
from contextlib import contextmanager
from http.server import HTTPServer
from pathlib import Path
from typing import Iterator, Optional

import pytest

from backend import web
from backend.models import Part
from backend.web import WebUIRequestHandler, _normalize_path, _render_home, _render_inventory


def test_render_home_includes_navigation_message() -> None:
    content = _render_home()

    assert "Use the navigation to access inventory data." in content


def test_render_inventory_empty_state() -> None:
    content = _render_inventory([])

    assert "No parts available." in content


def test_render_inventory_with_parts() -> None:
    parts = [
        Part(
            id="part-1",
            name="Resistor 1k",
            category_id="cat-1",
            manufacturer_id="mfg-1",
            drawer_id="drawer-1",
            tags=["resistor"],
            quantity=100,
        )
    ]

    content = _render_inventory(parts)

    assert "Resistor 1k" in content
    assert "100" in content


def test_render_inventory_html_structure() -> None:
    content = _render_inventory([])

    assert "<title>Inventory</title>" in content
    assert "<nav>" in content
    assert "<table>" in content


def test_normalize_path_strips_trailing_slash() -> None:
    assert _normalize_path("/inventory/") == "/inventory"
    assert _normalize_path("/") == "/"


def test_normalize_path_strips_index_html() -> None:
    assert _normalize_path("/inventory/index.html") == "/inventory"
    assert _normalize_path("/index.html") == "/"


def test_normalize_path_handles_extra_slashes_and_index_suffix() -> None:
    assert _normalize_path("//inventory//") == "/inventory"
    assert _normalize_path("/inventory/index.html/") == "/inventory"
    assert _normalize_path("/index.html/") == "/"


@contextmanager
def _running_server(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Spins up the real WebUIRequestHandler on a background thread, pointed at `repo_root`
    via the SMART_RACK_REPO_ROOT override, so export/import can be exercised as real HTTP
    requests (body parsing, file writes) rather than just the pure render functions above."""
    monkeypatch.setenv("SMART_RACK_REPO_ROOT", str(repo_root))
    web.reset_simulated_controller()
    server = HTTPServer(("127.0.0.1", 0), WebUIRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()


def _build_master_data_dir(tmp_path: Path) -> Path:
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
    return master_dir


def test_export_route_returns_master_data_as_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    master_dir = _build_master_data_dir(tmp_path)
    (master_dir / "racks.json").write_text(
        json.dumps(
            [{"id": "rack-1", "name": "Main", "wledInstance": "wled-main", "rows": 1, "drawersPerRow": 1}]
        ),
        encoding="utf-8",
    )

    with _running_server(tmp_path, monkeypatch) as base_url:
        with urllib.request.urlopen(f"{base_url}/export") as response:
            assert response.headers["Content-Type"] == "application/json; charset=utf-8"
            payload = json.loads(response.read())

    assert payload["racks"][0]["id"] == "rack-1"
    assert payload["parts"] == []


def test_import_route_round_trip_via_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _build_master_data_dir(tmp_path)

    import_payload = {
        "racks": [
            {
                "id": "rack-1",
                "name": "Main",
                "wledInstance": "wled-main",
                "rows": 1,
                "drawersPerRow": 1,
            }
        ]
    }

    with _running_server(tmp_path, monkeypatch) as base_url:
        body = urllib.parse.urlencode({"payload": json.dumps(import_payload)}).encode("utf-8")
        request = urllib.request.Request(f"{base_url}/import", data=body, method="POST")
        with urllib.request.urlopen(request) as response:
            assert response.status == 200
            assert "Import successful" in response.read().decode("utf-8")

        with urllib.request.urlopen(f"{base_url}/export") as response:
            exported = json.loads(response.read())

    assert exported["racks"] == import_payload["racks"]


def test_import_route_rejects_invalid_payload_and_shows_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _build_master_data_dir(tmp_path)

    with _running_server(tmp_path, monkeypatch) as base_url:
        body = urllib.parse.urlencode(
            {"payload": json.dumps({"racks": [{"id": "rack-1"}]})}
        ).encode("utf-8")
        request = urllib.request.Request(f"{base_url}/import", data=body, method="POST")
        with urllib.request.urlopen(request) as response:
            html = response.read().decode("utf-8")
            assert "Import failed" in html
            assert "racks[0]" in html

        with urllib.request.urlopen(f"{base_url}/export") as response:
            exported = json.loads(response.read())

    # nothing was written since the payload was invalid
    assert exported["racks"] == []


def _write_simulate_fixture(tmp_path: Path, wled_devices: Optional[list] = None) -> None:
    master_dir = _build_master_data_dir(tmp_path)
    (master_dir / "wled_devices.json").write_text(
        json.dumps(wled_devices if wled_devices is not None else []), encoding="utf-8"
    )
    (master_dir / "racks.json").write_text(
        json.dumps(
            [{"id": "rack-1", "name": "Main", "wledInstance": "wled-main", "rows": 1, "drawersPerRow": 2}]
        ),
        encoding="utf-8",
    )
    (master_dir / "drawers.json").write_text(
        json.dumps(
            [
                {
                    "id": "drawer-a",
                    "rackId": "rack-1",
                    "row": 0,
                    "col": 0,
                    "label": "A",
                    "pixelRange": {"start": 0, "count": 5},
                },
                {
                    "id": "drawer-b",
                    "rackId": "rack-1",
                    "row": 0,
                    "col": 1,
                    "label": "B",
                    "pixelRange": {"start": 5, "count": 5},
                },
            ]
        ),
        encoding="utf-8",
    )
    (master_dir / "parts.json").write_text(
        json.dumps(
            [
                {
                    "id": "part-1",
                    "name": "Resistor 1k",
                    "categoryId": "cat-1",
                    "manufacturerId": "mfg-1",
                    "drawerId": "drawer-a",
                    "tags": [],
                    "quantity": 10,
                }
            ]
        ),
        encoding="utf-8",
    )


def test_simulate_route_highlights_matching_drawer_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_simulate_fixture(tmp_path)

    with _running_server(tmp_path, monkeypatch) as base_url:
        with urllib.request.urlopen(f"{base_url}/simulate?q=resistor") as response:
            html = response.read().decode("utf-8")

    assert "rgb(0,255,0)" in html  # drawer-a, matched
    assert "rgb(0,0,0)" in html  # drawer-b, not matched
    assert ">A<" in html
    assert ">B<" in html


def test_simulate_route_clears_highlight_when_query_is_cleared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_simulate_fixture(tmp_path)

    with _running_server(tmp_path, monkeypatch) as base_url:
        with urllib.request.urlopen(f"{base_url}/simulate?q=resistor") as response:
            assert "rgb(0,255,0)" in response.read().decode("utf-8")

        with urllib.request.urlopen(f"{base_url}/simulate") as response:
            html = response.read().decode("utf-8")

    assert "rgb(0,255,0)" not in html
    assert html.count("rgb(0,0,0)") == 2


def test_simulate_route_shows_simulated_badge_when_device_not_connected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_simulate_fixture(
        tmp_path,
        wled_devices=[{"id": "wled-main", "host": "127.0.0.1:1", "hardwareConnected": False}],
    )

    with _running_server(tmp_path, monkeypatch) as base_url:
        with urllib.request.urlopen(f"{base_url}/simulate") as response:
            html = response.read().decode("utf-8")

    assert "(simulated)" in html
    assert "live" not in html
    assert "Hardware unreachable" not in html  # device isn't connected, so no hardware call


def test_simulate_route_reports_unreachable_hardware_without_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_simulate_fixture(
        tmp_path,
        wled_devices=[{"id": "wled-main", "host": "127.0.0.1:1", "hardwareConnected": True}],
    )

    with _running_server(tmp_path, monkeypatch) as base_url:
        with urllib.request.urlopen(f"{base_url}/simulate?q=resistor") as response:
            assert response.status == 200
            html = response.read().decode("utf-8")

    assert "live" in html  # badge still shows the device as configured-connected
    assert "Hardware unreachable" in html
    assert "wled-main" in html
    assert "rgb(0,255,0)" in html  # simulation still highlighted despite the hardware failure
