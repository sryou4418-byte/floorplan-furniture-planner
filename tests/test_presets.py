from planner.models import Project
from planner.presets import ASSET_ROOT, ROOM_PRESETS


def test_all_room_presets_have_images_and_valid_dimensions():
    assert len(ROOM_PRESETS) == 23
    for preset in ROOM_PRESETS:
        assert preset.width_mm > 0
        assert preset.depth_mm > 0
        assert (ASSET_ROOT / preset.image_file).is_file()


def test_applying_preset_replaces_room_and_clears_furniture():
    project = Project()
    ROOM_PRESETS[0].apply(project)
    assert project.room.name == "보건실"
    assert project.room.width_mm == 3440
    assert project.room.depth_mm == 8750
    assert project.plan_image_bytes
