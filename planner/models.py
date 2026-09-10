from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from math import isfinite
from uuid import uuid4


SCHEMA_VERSION = 1


@dataclass(slots=True)
class Room:
    width_mm: float = 3600.0
    depth_mm: float = 3200.0
    name: str = "공간"

    def validate(self) -> None:
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)
                   for v in (self.width_mm, self.depth_mm)):
            raise ValueError("공간 치수는 유한한 숫자여야 합니다.")
        if self.width_mm <= 0 or self.depth_mm <= 0:
            raise ValueError("공간의 가로와 세로는 0보다 커야 합니다.")


@dataclass(slots=True)
class Furniture:
    name: str
    width_mm: float
    depth_mm: float
    x_mm: float = 0.0
    y_mm: float = 0.0
    rotation: int = 0
    group: str = ""
    clearance_mm: float = 0.0
    id: str = field(default_factory=lambda: uuid4().hex)
    shape: str = "rectangle"

    def validate(self) -> None:
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)
                   for v in (self.width_mm, self.depth_mm, self.x_mm, self.y_mm, self.clearance_mm)):
            raise ValueError("치수와 위치는 유한한 숫자여야 합니다.")
        if self.shape not in ("rectangle", "circle"):
            raise ValueError("지원하지 않는 가구 모양입니다.")
        if self.shape == "circle" and self.width_mm != self.depth_mm:
            raise ValueError("원형 가구의 가로·세로는 같은 지름이어야 합니다.")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 80:
            raise ValueError("가구 이름은 1~80자로 입력해 주세요.")
        if self.width_mm <= 0 or self.depth_mm <= 0:
            raise ValueError("가구의 가로와 세로는 0보다 커야 합니다.")
        if self.rotation not in (0, 90):
            raise ValueError("첫 버전에서는 0도와 90도 회전만 지원합니다.")
        if self.clearance_mm < 0:
            raise ValueError("여유 공간은 0 이상이어야 합니다.")


@dataclass(slots=True)
class Project:
    room: Room = field(default_factory=Room)
    furniture: list[Furniture] = field(default_factory=list)
    plan_image_name: str | None = None
    plan_image_mime: str | None = None
    plan_image_bytes: bytes | None = field(default=None, repr=False)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "room": asdict(self.room),
            "furniture": [asdict(item) for item in self.furniture],
            "plan_image_name": self.plan_image_name,
            "plan_image_mime": self.plan_image_mime,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("지원하지 않는 프로젝트 버전입니다.")
        room = Room(**data["room"])
        room.validate()
        furniture = [Furniture(**item) for item in data.get("furniture", [])]
        for item in furniture:
            item.validate()
        return cls(
            room=room,
            furniture=furniture,
            plan_image_name=data.get("plan_image_name"),
            plan_image_mime=data.get("plan_image_mime"),
        )
