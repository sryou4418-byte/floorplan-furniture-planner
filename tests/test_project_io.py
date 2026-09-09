import pytest

from planner.models import Furniture, Project, Room
from planner.project_io import export_project, import_project


def test_project_round_trip():
    project = Project(
        room=Room(4200, 3100, "안방"),
        furniture=[Furniture("침대", 1600, 2000, 100, 200, group="침실")],
        plan_image_name="plan.png",
        plan_image_mime="image/png",
        plan_image_bytes=b"image bytes",
    )
    restored = import_project(export_project(project))
    assert restored.to_dict() == project.to_dict()
    assert restored.plan_image_bytes == b"image bytes"


def test_invalid_archive_is_rejected():
    with pytest.raises(ValueError):
        import_project(b"not a project")
