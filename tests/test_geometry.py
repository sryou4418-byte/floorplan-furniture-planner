import pytest

from planner.geometry import analyze, effective_size, occupied_ratio, overlap_depth, overlaps
from planner.models import Furniture, Room


def furniture(name="A", **kwargs):
    defaults = dict(width_mm=1000, depth_mm=500, x_mm=0, y_mm=0)
    defaults.update(kwargs)
    return Furniture(name=name, **defaults)


def test_exact_fit_is_allowed():
    room = Room(width_mm=1000, depth_mm=500)
    item = furniture()
    status = analyze(room, item, [item])
    assert status.inside_room
    assert status.level == "ok"


def test_one_millimeter_overflow_is_rejected():
    room = Room(width_mm=1000, depth_mm=500)
    item = furniture(x_mm=1)
    status = analyze(room, item, [item])
    assert not status.inside_room
    assert status.overflow_mm == pytest.approx(1)


def test_rotation_swaps_effective_dimensions():
    item = furniture(width_mm=1200, depth_mm=600, rotation=90)
    assert effective_size(item) == (600, 1200)


def test_touching_edges_do_not_overlap():
    a = furniture(width_mm=500, depth_mm=500)
    b = furniture("B", width_mm=500, depth_mm=500, x_mm=500)
    assert overlap_depth(a, b) == (0, 500)
    assert not overlaps(a, b)


def test_partial_overlap_is_reported():
    a = furniture(width_mm=500, depth_mm=500)
    b = furniture("B", width_mm=500, depth_mm=500, x_mm=450)
    assert overlaps(a, b)
    assert analyze(Room(2000, 2000), a, [a, b]).overlaps == ("B",)


def test_clearance_warning():
    room = Room(2000, 2000)
    item = furniture(x_mm=50, y_mm=50, clearance_mm=100)
    assert analyze(room, item, [item]).level == "warning"


def test_occupied_ratio():
    room = Room(2000, 1000)
    assert occupied_ratio(room, [furniture(width_mm=1000, depth_mm=500)]) == pytest.approx(0.25)
