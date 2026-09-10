import pytest

from planner.actions import apply_action, base_furniture_name, furniture_name_counts, move_furniture
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
    assert copy.id != item.id and copy.rotation == 90 and copy.name == "새 책상 2"
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


def test_copy_uses_first_available_number_without_suffix_stacking():
    original = Furniture("책상", 100, 100)
    second = Furniture("책상 2", 100, 100, x_mm=200)
    project = Project(Room(1000, 1000), [original, second])
    [third_id] = apply_action(project, "copy", second.id)
    assert next(item.name for item in project.furniture if item.id == third_id) == "책상 3"
    project.furniture = [item for item in project.furniture if item.id != second.id]
    [reused_id] = apply_action(project, "copy", original.id)
    assert next(item.name for item in project.furniture if item.id == reused_id) == "책상 2"


def test_count_names_ignore_outer_space_and_trailing_sequence_number():
    project = Project(
        furniture=[
            Furniture("책상", 100, 100),
            Furniture("책상1", 100, 100),
            Furniture("책상 2", 100, 100),
            Furniture(" 책상3 ", 100, 100),
            Furniture("2단 수납장", 100, 100),
            Furniture("3단 수납장", 100, 100),
        ]
    )
    assert furniture_name_counts(project) == {
        "책상": 4,
        "2단 수납장": 1,
        "3단 수납장": 1,
    }
    assert base_furniture_name("책상 복사 복사") == "책상"


def test_move_clamps_single_and_group_without_changing_relative_spacing():
    a = Furniture("a", 200, 100, x_mm=100, y_mm=100)
    b = Furniture("b", 100, 100, x_mm=400, y_mm=300)
    project = Project(Room(1000, 800), [a, b])
    move_furniture(
        project,
        [
            {"id": a.id, "x_mm": 850, "y_mm": 700},
            {"id": b.id, "x_mm": 1150, "y_mm": 900},
        ],
    )
    assert (a.x_mm, a.y_mm) == (600, 500)
    assert (b.x_mm, b.y_mm) == (900, 700)


def test_oversized_item_remains_recoverable_without_resizing():
    item = Furniture("큰 가구", 1200, 900, x_mm=100, y_mm=100)
    project = Project(Room(1000, 800), [item])
    move_furniture(project, [{"id": item.id, "x_mm": -900, "y_mm": -700}])
    assert (item.x_mm, item.y_mm, item.width_mm, item.depth_mm) == (0, 0, 1200, 900)


def test_edit_and_rotation_keep_furniture_recoverable():
    item = Furniture("장", 400, 200, x_mm=600, y_mm=700)
    project = Project(Room(1000, 800), [item])
    apply_action(project, "rotate", item.id)
    assert (item.x_mm, item.y_mm, item.rotation) == (600, 400, 90)
    from planner.actions import edit_furniture

    edit_furniture(project, item.id, {"width_mm": 900, "depth_mm": 1200})
    assert (item.x_mm, item.y_mm, item.width_mm, item.depth_mm) == (0, 0, 900, 1200)
