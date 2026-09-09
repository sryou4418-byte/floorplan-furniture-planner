import pytest

from planner.actions import apply_action
from planner.geometry import is_inside, overlaps
from planner.models import Furniture, Project, Room
from planner.workspace import Workspace, export_workspace, import_workspace


def test_commands_survive_room_switch_and_archive():
    work = Workspace()
    project = work.open_room("1층 · 컴퓨터")
    item = Furniture("책상", 1200, 600, group="A")
    project.furniture.append(item)
    apply_action(project, "rename", item.id, "새 책상")
    apply_action(project, "rotate", item.id)
    ids = apply_action(project, "copy", item.id)
    copy = next(f for f in project.furniture if f.id in ids)
    assert copy.id != item.id and copy.rotation == 90
    assert copy.group == ""
    assert is_inside(project.room, copy) and not overlaps(item, copy)
    work.open_room("2층 · 1-5")
    restored = import_workspace(export_workspace(work)).open_room("1층 · 컴퓨터")
    assert restored.furniture[0].name == "새 책상"
    assert restored.furniture[0].rotation == 90
    apply_action(restored, "delete", item.id)
    assert [f.id for f in restored.furniture] == ids


def test_failed_copy_and_rename_do_not_modify_room():
    item = Furniture("원본", 1000, 1000)
    project = Project(Room(1000, 1000), [item])
    with pytest.raises(ValueError):
        apply_action(project, "copy", item.id)
    with pytest.raises(ValueError):
        apply_action(project, "rename", item.id, "   ")
    assert project.furniture == [item] and item.name == "원본"


def test_circle_rotation_is_noop():
    item = Furniture("원탁", 900, 900, shape="circle")
    project = Project(furniture=[item])
    apply_action(project, "rotate", item.id)
    assert item.rotation == 0
