from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple

from .models import Part, PixelRange
from .services import MasterDataService

Color = Tuple[int, int, int]
GREEN: Color = (0, 255, 0)
OFF: Color = (0, 0, 0)


class WledController(ABC):
    """Interface for driving a WLED instance's pixels. Implementations:
    - MockWledController: records calls instead of making network requests, so pick-by-light
      logic can be built and tested without any real ESP32/WLED hardware.
    - A future HttpWledController, calling WLED's JSON HTTP API, once real hardware exists — not
      implemented yet (see docs/decisions.md)."""

    @abstractmethod
    def set_pixels(self, wled_instance: str, pixel_range: PixelRange, color: Color) -> None:
        ...


@dataclass
class MockWledController(WledController):
    """Records the last color set per (wled_instance, pixel range) instead of talking to real
    hardware. `color_for` lets a caller (e.g. the web simulation view) read back what would be
    shown on the physical rack."""

    _state: Dict[Tuple[str, int, int], Color] = field(default_factory=dict)

    def set_pixels(self, wled_instance: str, pixel_range: PixelRange, color: Color) -> None:
        self._state[(wled_instance, pixel_range.start, pixel_range.count)] = color

    def color_for(self, wled_instance: str, pixel_range: PixelRange) -> Color:
        return self._state.get((wled_instance, pixel_range.start, pixel_range.count), OFF)


class PickByLightService:
    """Implements the pick-by-light behavior described in README.md: given a set of matching
    parts, light every drawer containing one of them green, and explicitly turn every other
    configured drawer off (not just leave it — a previous search's highlights must be cleared)."""

    def __init__(self, master_service: MasterDataService, controller: WledController) -> None:
        self._master = master_service
        self._controller = controller

    def highlight_parts(self, parts: Sequence[Part]) -> None:
        matching_drawer_ids = {part.drawer_id for part in parts}
        racks_by_id = {rack.id: rack for rack in self._master.list_racks()}
        for drawer in self._master.list_drawers():
            rack = racks_by_id.get(drawer.rack_id)
            if rack is None:
                continue
            color = GREEN if drawer.id in matching_drawer_ids else OFF
            self._controller.set_pixels(rack.wled_instance, drawer.pixel_range, color)
