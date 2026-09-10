"""Furniture commands shared by pointer, touch and form controls."""
from dataclasses import replace
from uuid import uuid4
from math import isfinite

from .geometry import bounds, effective_size, is_inside, overlaps
from .models import Furniture, Project


def create_sample(project: Project, x: float, y: float) -> list[str]:
    if not all(isinstance(v, (int, float)) and isfinite(v) for v in (x, y)):
        raise ValueError("위치가 올바르지 않습니다.")
    scale = min(1, project.room.width_mm / 1200, project.room.depth_mm / 600)
    w, d = 1200 * scale, 600 * scale
    item = Furniture("샘플 가구", w, d,
                     x_mm=max(0, min(x - w / 2, project.room.width_mm - w)),
                     y_mm=max(0, min(y - d / 2, project.room.depth_mm - d)))
    item.validate()
    project.furniture.append(item)
    return [item.id]


def edit_furniture(project: Project, item_id: str, changes: dict) -> list[str]:
    item = next((f for f in project.furniture if f.id == item_id), None)
    if item is None:
        raise ValueError("선택한 가구를 찾을 수 없습니다.")
    allowed = {"name", "shape", "width_mm", "depth_mm", "x_mm", "y_mm", "clearance_mm", "group"}
    values = {k: v for k, v in changes.items() if k in allowed}
    if "name" in values and isinstance(values["name"], str):
        values["name"] = values["name"].strip()
    candidate = replace(item, **values)
    if candidate.shape == "circle":
        candidate.depth_mm = candidate.width_mm
        candidate.rotation = 0
    candidate.validate()  # Validate before mutating any live state.
    for key in allowed | {"rotation"}:
        setattr(item, key, getattr(candidate, key))
    return [item.id]


def move_furniture(project: Project, moves: list[dict]) -> list[str]:
    updates = []
    by_id = {f.id: f for f in project.furniture}
    for move in moves:
        item = by_id.get(move.get("id"))
        if item is None:
            continue
        candidate = replace(item, x_mm=move.get("x_mm"), y_mm=move.get("y_mm"))
        candidate.validate()
        updates.append((item, candidate))
    for item, candidate in updates:
        item.x_mm, item.y_mm = round(candidate.x_mm, 1), round(candidate.y_mm, 1)
    return [item.id for item, _ in updates]


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
