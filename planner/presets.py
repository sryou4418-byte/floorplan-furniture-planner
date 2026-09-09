from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Project, Room


ASSET_ROOT = Path(__file__).resolve().parent.parent / "assets" / "rooms"


@dataclass(frozen=True, slots=True)
class RoomPreset:
    floor: str
    name: str
    width_mm: float
    depth_mm: float
    image_file: str

    @property
    def label(self) -> str:
        return f"{self.floor} · {self.name}"

    def apply(self, project: Project) -> None:
        project.room = Room(self.width_mm, self.depth_mm, self.name)
        project.furniture.clear()
        project.plan_image_name = self.image_file
        project.plan_image_mime = "image/png"
        project.plan_image_bytes = (ASSET_ROOT / self.image_file).read_bytes()


ROOM_PRESETS = (
    RoomPreset("1층", "보건실", 3440, 8750, "1f_nurse_office.png"),
    RoomPreset("1층", "컴퓨터", 6880, 8750, "1f_computer.png"),
    RoomPreset("1층", "간호의기초", 6880, 8750, "1f_nursing_basics.png"),
    RoomPreset("1층", "피부미용", 13760, 8750, "1f_skin_beauty.png"),
    RoomPreset("1층", "기초간호임상", 13760, 8750, "1f_clinical_nursing.png"),
    RoomPreset("1층", "여행서비스", 6880, 8750, "1f_travel_service.png"),
    RoomPreset("1층", "바리스타", 13760, 8750, "1f_barista.png"),
    RoomPreset("1층", "바텐더+호텔", 13760, 8750, "1f_bartender_hotel.png"),
    RoomPreset("1층", "제과제빵", 13760, 8750, "1f_bakery.png"),
    RoomPreset("2층", "교무실2", 3440, 8750, "2f_staff_2.png"),
    RoomPreset("2층", "1-5", 6880, 8750, "2f_class_1_5.png"),
    RoomPreset("2층", "2-5", 6880, 8750, "2f_class_2_5.png"),
    RoomPreset("2층", "2-4", 6880, 8750, "2f_class_2_4.png"),
    RoomPreset("2층", "2-3", 6880, 8750, "2f_class_2_3.png"),
    RoomPreset("2층", "2-2", 6880, 8750, "2f_class_2_2.png"),
    RoomPreset("2층", "2-1", 6880, 8750, "2f_class_2_1.png"),
    RoomPreset("2층", "교무실1", 10320, 8750, "2f_staff_1.png"),
    RoomPreset("2층", "3-1", 6880, 8750, "2f_class_3_1.png"),
    RoomPreset("2층", "3-2", 6880, 8750, "2f_class_3_2.png"),
    RoomPreset("2층", "3-3", 6880, 8750, "2f_class_3_3.png"),
    RoomPreset("2층", "3-4", 6880, 8750, "2f_class_3_4.png"),
    RoomPreset("2층", "3-5", 6880, 8750, "2f_class_3_5.png"),
    RoomPreset("2층", "교육복지", 6880, 8750, "2f_welfare.png"),
)

PRESETS_BY_LABEL = {preset.label: preset for preset in ROOM_PRESETS}
