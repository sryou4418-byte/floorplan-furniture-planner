from __future__ import annotations

from dataclasses import dataclass
from math import hypot, pi

from .models import Furniture, Room


EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def depth(self) -> float:
        return self.bottom - self.top


@dataclass(frozen=True, slots=True)
class PlacementStatus:
    inside_room: bool
    clearance_ok: bool
    overlaps: tuple[str, ...]
    overflow_mm: float
    minimum_wall_gap_mm: float

    @property
    def level(self) -> str:
        if not self.inside_room or self.overlaps:
            return "error"
        if not self.clearance_ok:
            return "warning"
        return "ok"


def effective_size(item: Furniture) -> tuple[float, float]:
    if item.rotation == 90:
        return item.depth_mm, item.width_mm
    return item.width_mm, item.depth_mm


def bounds(item: Furniture, padding: float = 0.0) -> Bounds:
    width, depth = effective_size(item)
    return Bounds(
        item.x_mm - padding,
        item.y_mm - padding,
        item.x_mm + width + padding,
        item.y_mm + depth + padding,
    )


def overflow_amount(room: Room, item: Furniture) -> float:
    box = bounds(item)
    return max(0.0, -box.left, -box.top, box.right - room.width_mm, box.bottom - room.depth_mm)


def is_inside(room: Room, item: Furniture, padding: float = 0.0) -> bool:
    box = bounds(item, padding)
    return (
        box.left >= -EPSILON
        and box.top >= -EPSILON
        and box.right <= room.width_mm + EPSILON
        and box.bottom <= room.depth_mm + EPSILON
    )


def overlap_depth(a: Furniture, b: Furniture) -> tuple[float, float]:
    aa, bb = bounds(a), bounds(b)
    return min(aa.right, bb.right) - max(aa.left, bb.left), min(aa.bottom, bb.bottom) - max(aa.top, bb.top)


def overlaps(a: Furniture, b: Furniture) -> bool:
    if a.shape == "circle" or b.shape == "circle":
        circle, other = (a, b) if a.shape == "circle" else (b, a)
        radius = circle.width_mm / 2
        cx, cy = circle.x_mm + radius, circle.y_mm + radius
        if other.shape == "circle":
            r2 = other.width_mm / 2
            return hypot(cx - other.x_mm - r2, cy - other.y_mm - r2) < radius + r2 - EPSILON
        box = bounds(other)
        closest_x = min(max(cx, box.left), box.right)
        closest_y = min(max(cy, box.top), box.bottom)
        return hypot(cx - closest_x, cy - closest_y) < radius - EPSILON
    overlap_x, overlap_y = overlap_depth(a, b)
    return overlap_x > EPSILON and overlap_y > EPSILON


def minimum_wall_gap(room: Room, item: Furniture) -> float:
    box = bounds(item)
    return min(box.left, box.top, room.width_mm - box.right, room.depth_mm - box.bottom)


def analyze(room: Room, item: Furniture, all_items: list[Furniture]) -> PlacementStatus:
    collisions = tuple(other.name for other in all_items if other.id != item.id and overlaps(item, other))
    return PlacementStatus(
        inside_room=is_inside(room, item),
        clearance_ok=is_inside(room, item, item.clearance_mm),
        overlaps=collisions,
        overflow_mm=overflow_amount(room, item),
        minimum_wall_gap_mm=minimum_wall_gap(room, item),
    )


def occupied_ratio(room: Room, items: list[Furniture]) -> float:
    room_area = room.width_mm * room.depth_mm
    if room_area <= 0:
        return 0.0
    return sum(pi * (item.width_mm / 2) ** 2 if item.shape == "circle"
               else item.width_mm * item.depth_mm for item in items) / room_area
