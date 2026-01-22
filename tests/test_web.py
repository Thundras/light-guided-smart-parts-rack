from backend.models import Part
from backend.web import _normalize_path, _render_home, _render_inventory


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
