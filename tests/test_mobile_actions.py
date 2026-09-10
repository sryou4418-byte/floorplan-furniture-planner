from math import inf, nan

import pytest

from planner.actions import create_sample, edit_furniture, move_furniture
from planner.models import Furniture, Project, Room
from planner.workspace import Workspace, export_workspace, import_workspace


def test_tap_sample_edges_and_small_room():
    p = Project(Room(1000, 400))
    create_sample(p, 999, 399)
    f = p.furniture[0]
    assert (f.width_mm, f.depth_mm) == (800, 400)
    assert (f.x_mm, f.y_mm) == (200, 0)
    create_sample(p, 0, 0)
    assert p.furniture[1].x_mm == p.furniture[1].y_mm == 0


def test_mobile_edit_move_room_archive_roundtrip():
    work = Workspace()
    p = work.open_room("1층 · 컴퓨터")
    [fid] = create_sample(p, 2000, 3000)
    edit_furniture(p, fid, {"name": " 원탁 ", "shape": "circle", "width_mm": 900})
    move_furniture(p, [{"id": fid, "x_mm": 1234.56, "y_mm": 2222}])
    work.open_room("1층 · 보건실")
    work.open_room("1층 · 컴퓨터")
    restored = import_workspace(export_workspace(work)).project.furniture[0]
    assert (restored.name, restored.shape, restored.width_mm, restored.depth_mm) == ("원탁", "circle", 900, 900)
    assert restored.x_mm == 1234.6
    assert restored.rotation == 0
    edit_furniture(p, fid, {"shape": "rectangle", "width_mm": 1200, "depth_mm": 650})
    assert p.furniture[0].depth_mm == 650


@pytest.mark.parametrize("value", [nan, inf, -inf, 0, -1])
def test_invalid_edit_never_partially_changes_live_item(value):
    p = Project(furniture=[Furniture("기존", 1200, 600)])
    with pytest.raises(ValueError):
        edit_furniture(p, p.furniture[0].id, {"name": "변경", "width_mm": value})
    assert p.furniture[0].name == "기존"
    assert p.furniture[0].width_mm == 1200


def test_group_move_is_atomic_and_ignores_deleted_ids():
    a, b = Furniture("a", 100, 100), Furniture("b", 100, 100)
    p = Project(furniture=[a, b])
    with pytest.raises(ValueError):
        move_furniture(p, [{"id": a.id, "x_mm": 100, "y_mm": 100}, {"id": b.id, "x_mm": nan, "y_mm": 200}])
    assert a.x_mm == b.x_mm == 0
    assert move_furniture(p, [{"id": "deleted", "x_mm": 1, "y_mm": 1}]) == []


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_file_model_rejects_nonfinite_coordinates(value):
    with pytest.raises(ValueError):
        Room(value, 100).validate()
    p = Project(furniture=[Furniture("bad", 100, 100, x_mm=value)])
    with pytest.raises(ValueError):
        Project.from_dict(p.to_dict())
