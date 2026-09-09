from datetime import datetime, timezone
from math import pi

import pytest
from streamlit.testing.v1 import AppTest

from planner.geometry import occupied_ratio, overlaps
from planner.models import Furniture, Project, Room
from planner.project_io import export_project
from planner.workspace import Workspace, download_name, export_workspace, import_workspace


def test_room_switch_and_archive_roundtrip():
    work = Workspace()
    first = work.open_room("1층 · 컴퓨터")
    first.furniture.append(Furniture("책상", 1200, 600, x_mm=350, group="A"))
    second = work.open_room("2층 · 1-5")
    second.furniture.append(Furniture("원탁", 900, 900, shape="circle"))
    assert work.open_room("1층 · 컴퓨터") is first
    restored = import_workspace(export_workspace(work))
    assert restored.active == "1층 · 컴퓨터"
    assert restored.project.furniture[0].x_mm == 350
    assert restored.project.furniture[0].group == "A"
    assert restored.open_room("2층 · 1-5").furniture[0].shape == "circle"
    assert restored.project.plan_image_bytes == second.plan_image_bytes


def test_legacy_import_and_filename():
    work = Workspace()
    project = work.open_room("1층 · 컴퓨터")
    restored = import_workspace(export_project(project))
    assert restored.active == work.active
    assert download_name(work, datetime(2026, 9, 10, 23, 1, 2, tzinfo=timezone.utc)) == "1층_컴퓨터_20260911_080102.fplan"
    work.project.room.name = 'a/b:c?'
    assert "a_b_c_" in download_name(work)


def test_circular_geometry():
    a = Furniture("A", 100, 100, shape="circle")
    b = Furniture("B", 100, 100, x_mm=90, y_mm=90, shape="circle")
    assert not overlaps(a, b)  # Bounding squares overlap, actual circles do not.
    b.x_mm, b.y_mm = 100, 0
    assert not overlaps(a, b)  # Tangency is not collision.
    b.x_mm = 99
    assert overlaps(a, b)
    corner = Furniture("corner", 10, 10, x_mm=95, y_mm=95)
    assert not overlaps(a, corner)
    assert not overlaps(corner, a)
    corner.x_mm, corner.y_mm = 45, 45
    assert overlaps(a, corner)
    assert occupied_ratio(Room(100, 100), [a]) == pytest.approx(pi / 4)
    with pytest.raises(ValueError):
        Furniture("bad", 100, 50, shape="circle").validate()


def test_app_room_switch_retains_furniture():
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    assert not at.exception
    at.selectbox[0].select("1층 · 컴퓨터").run()
    next(b for b in at.button if b.label == "선택한 호실 열기").click().run()
    next(t for t in at.text_input if t.label == "가구 이름").set_value("책상")
    next(b for b in at.button if b.label == "가구 추가").click().run()
    assert len(at.session_state.project.furniture) == 1
    at.selectbox[0].select("2층 · 1-5").run()
    next(b for b in at.button if b.label == "선택한 호실 열기").click().run()
    assert len(at.session_state.project.furniture) == 0
    at.selectbox[0].select("1층 · 컴퓨터").run()
    next(b for b in at.button if b.label == "선택한 호실 열기").click().run()
    assert at.session_state.project.furniture[0].name == "책상"
    assert not at.exception


def test_old_model_defaults_to_rectangle():
    data = Project(furniture=[Furniture("old", 100, 100)]).to_dict()
    del data["furniture"][0]["shape"]
    assert Project.from_dict(data).furniture[0].shape == "rectangle"
