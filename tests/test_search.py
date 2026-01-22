from typing import List

from backend.models import Part
from backend.services import PartSearchCriteria, PartSearchService


class StubMasterStore:
    def __init__(self, parts: List[Part]) -> None:
        self._parts = parts

    def load_parts(self) -> List[Part]:
        return list(self._parts)


def _sample_parts() -> List[Part]:
    return [
        Part(
            id="part-1",
            name="Resistor 1k",
            category_id="cat-res",
            manufacturer_id="mfg-1",
            drawer_id="drawer-a",
            tags=["resistor", "through-hole"],
            quantity=100,
            notes="Standard carbon film",
        ),
        Part(
            id="part-2",
            name="Capacitor 10uF",
            category_id="cat-cap",
            manufacturer_id="mfg-2",
            drawer_id="drawer-b",
            tags=["capacitor"],
            quantity=25,
        ),
        Part(
            id="part-3",
            name="Resistor 10k",
            category_id="cat-res",
            manufacturer_id="mfg-1",
            drawer_id="drawer-a",
            tags=["resistor", "smd"],
            quantity=5,
        ),
    ]


def test_search_without_filters_returns_all_parts() -> None:
    service = PartSearchService(StubMasterStore(_sample_parts()))

    results = service.search_parts(PartSearchCriteria())

    assert [part.id for part in results] == ["part-1", "part-2", "part-3"]


def test_search_matches_query_across_name_and_notes() -> None:
    service = PartSearchService(StubMasterStore(_sample_parts()))

    results = service.search_parts(PartSearchCriteria(query="carbon"))

    assert [part.id for part in results] == ["part-1"]


def test_search_filters_by_tags_and_quantity_range() -> None:
    service = PartSearchService(StubMasterStore(_sample_parts()))

    criteria = PartSearchCriteria(tags_any=["resistor"], min_quantity=10, max_quantity=150)
    results = service.search_parts(criteria)

    assert [part.id for part in results] == ["part-1"]


def test_search_requires_all_tags_when_specified() -> None:
    service = PartSearchService(StubMasterStore(_sample_parts()))

    criteria = PartSearchCriteria(tags_all=["resistor", "smd"])
    results = service.search_parts(criteria)

    assert [part.id for part in results] == ["part-3"]
