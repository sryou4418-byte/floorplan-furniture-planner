import pytest

from planner.actions import utility_action
from planner.models import Project
from planner.project_io import export_project, import_project
from planner.workspace import Workspace, export_workspace, import_workspace


def add(project, kind="water", x=100, y=200):
    utility_action(project, {"action": "utility_create", "kind": kind, "x_mm": x, "y_mm": y})


def test_utilities_survive_room_switch_and_file_roundtrip():
    work = Workspace()
    for kind in ("water", "electric", "three_phase"):
        add(work.project, kind)
    original = work.project.to_dict()
    work.open_room("1층 · 컴퓨터")
    assert work.project.utility_points == []
    add(work.project, "electric", 500, 600)
    work.open_room("직접 설정")
    assert work.project.to_dict() == original
    restored = import_workspace(export_workspace(work))
    assert restored.project.to_dict() == original
    restored.open_room("1층 · 컴퓨터")
    assert restored.project.utility_points[0].x_mm == 500
    assert restored.project.furniture == []


def test_delete_only_requested_point_and_legacy_files():
    project = Project()
    add(project)
    add(project, "electric")
    first, second = project.utility_points
    utility_action(project, {"action": "utility_delete", "id": first.id})
    assert project.utility_points == [second]
    assert import_project(export_project(project)).utility_points == [second]
    legacy = project.to_dict()
    del legacy["utility_points"]
    assert Project.from_dict(legacy).utility_points == []


@pytest.mark.parametrize("kind,x,y", [
    ("gas", 0, 0), ("water", float("nan"), 0), ("water", 0, float("inf")),
    ("electric", -1, 0), ("three_phase", 100000, 0), ("water", True, 0),
])
def test_invalid_point_does_not_mutate_project(kind, x, y):
    project = Project()
    with pytest.raises(ValueError):
        add(project, kind, x, y)
    assert project.utility_points == []


def test_invalid_imported_point_rejected():
    data = Project().to_dict()
    data["utility_points"] = [{"kind": "water", "x_mm": "100", "y_mm": 0}]
    with pytest.raises(ValueError):
        Project.from_dict(data)
