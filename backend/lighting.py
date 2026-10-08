from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Sequence, Tuple

from .models import Part, PixelRange, WledDevice
from .services import MasterDataService

Color = Tuple[int, int, int]
GREEN: Color = (0, 255, 0)
OFF: Color = (0, 0, 0)


class WledController(ABC):
    """Interface for driving a WLED instance's pixels. Implementations:
    - MockWledController: records calls instead of making network requests, so pick-by-light
      logic can be built and tested without any real ESP32/WLED hardware.
    - HttpWledController: calls WLED's real JSON HTTP API. Not exercised against real hardware
      yet (none exists), but fully built and tested against a fake HTTP server — see
      docs/decisions.md.
    - DispatchingWledController: routes between the two per-WledDevice, based on that device's
      hardware_connected flag."""

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


class WledConnectionError(RuntimeError):
    """Raised by HttpWledController when a WLED device can't be reached or returns an error
    response. Callers (DispatchingWledController) catch this specifically — it's the expected,
    recoverable failure mode for "this ESP32 happens to be offline right now", not a programming
    error that should propagate."""


class HttpWledController(WledController):
    """Real WLED JSON HTTP API client — POST /json/state with a segment (`seg`) sets a pixel
    range to a solid color. `set_pixels`'s first argument is the device's network address
    (host, or host:port), not a WledDevice id: resolve the id to its `host` before calling this
    (DispatchingWledController does that).

    Not exercised against real hardware yet — none exists (see docs/decisions.md) — but it's a
    plain stdlib HTTP client, so it's fully testable against any fake server that implements the
    same request/response shape."""

    def __init__(self, timeout: float = 2.0) -> None:
        self._timeout = timeout

    def set_pixels(self, host: str, pixel_range: PixelRange, color: Color) -> None:
        url = f"http://{host}/json/state"
        body = json.dumps(
            {
                "seg": [
                    {
                        "start": pixel_range.start,
                        "stop": pixel_range.start + pixel_range.count,
                        "col": [[color[0], color[1], color[2]]],
                        "fx": 0,
                    }
                ]
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                response.read()
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise WledConnectionError(f"Could not reach WLED device at '{host}': {exc}") from exc


class DispatchingWledController(WledController):
    """Routes each set_pixels call by looking up the targeted WLED instance's WledDevice record
    (matched on Rack.wled_instance == WledDevice.id):
    - Always updates `simulated` (typically a MockWledController) regardless of hardware status,
      so /simulate keeps showing the logical pick-by-light state for every rack — "the
      visualization runs in parallel" even once hardware exists.
    - Additionally calls `hardware` (typically HttpWledController), resolving the device's `host`
      for the actual network address, but only when that device's hardware_connected flag is
      true. No matching device record, or hardware_connected=False, stays simulation-only — this
      is the per-ESP32 "go live" switch.
    - A hardware call failing (WledConnectionError — device offline, wrong host, etc.) is caught
      and reported via `on_hardware_error` rather than propagating, so one unreachable ESP32
      doesn't block pick-by-light for every other rack in the same request."""

    def __init__(
        self,
        master_service: MasterDataService,
        simulated: WledController,
        hardware: WledController,
        on_hardware_error: Optional[Callable[[str, WledConnectionError], None]] = None,
    ) -> None:
        self._master = master_service
        self._simulated = simulated
        self._hardware = hardware
        self._on_hardware_error = on_hardware_error or self._default_error_handler

    def set_pixels(self, wled_instance: str, pixel_range: PixelRange, color: Color) -> None:
        self._simulated.set_pixels(wled_instance, pixel_range, color)

        device = self._find_device(wled_instance)
        if device is None or not device.hardware_connected:
            return
        try:
            self._hardware.set_pixels(device.host, pixel_range, color)
        except WledConnectionError as exc:
            self._on_hardware_error(wled_instance, exc)

    def _find_device(self, wled_instance: str) -> Optional[WledDevice]:
        for device in self._master.list_wled_devices():
            if device.id == wled_instance:
                return device
        return None

    @staticmethod
    def _default_error_handler(wled_instance: str, exc: WledConnectionError) -> None:
        print(f"[lighting] WLED device '{wled_instance}' unreachable: {exc}", file=sys.stderr)


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
