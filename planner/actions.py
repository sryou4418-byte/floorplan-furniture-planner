"""Furniture commands shared by pointer, touch and form controls."""
from dataclasses import replace
from uuid import uuid4

from .geometry import bounds, effective_size, is_inside, overlaps
from .models import Project


def apply_action(project: Project, action: str, item_id: str, name: str = "") -> list[str]:
    item = next((f for f in project.furniture if f.id == item_id), None)
    if item is None:
        raise ValueError("선택한 가구를 찾을 수 없습니다.")
    if action == "rename":
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("이름은 1~80자로 입력해 주세요.")
        item.name = name
    elif action == "rotate":
        if item.shape != "circle":
            item.rotation = 90 if item.rotation == 0 else 0
    elif action == "delete":
        project.furniture = [f for f in project.furniture if f.id != item_id]
        return []
    elif action == "copy":
        copy = replace(item, id=uuid4().hex, name=f"{item.name[:74]} 복사", group="")
        width, depth = effective_size(copy)
        xs = {0.0, item.x_mm, project.room.width_mm - width}
        ys = {0.0, item.y_mm, project.room.depth_mm - depth}
        for other in project.furniture:
            box = bounds(other)
            xs.update((box.right + 50, box.left - width - 50))
            ys.update((box.bottom + 50, box.top - depth - 50))
        candidates = sorted(((x, y) for x in xs for y in ys),
                            key=lambda p: (p[0] - item.x_mm) ** 2 + (p[1] - item.y_mm) ** 2)
        for x, y in candidates:
            copy.x_mm, copy.y_mm = x, y
            if is_inside(project.room, copy) and not any(overlaps(copy, f) for f in project.furniture):
                project.furniture.append(copy)
                return [copy.id]
        raise ValueError("겹치지 않는 복사 위치를 찾지 못했어요. 주변 공간을 확보해 주세요.")
    else:
        raise ValueError("지원하지 않는 작업입니다.")
    return [item.id]
