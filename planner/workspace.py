"""Session-owned room layouts and portable multi-room archives. No shared storage."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
import json
import re
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile
from zoneinfo import ZoneInfo

from .models import Project
from .presets import PRESETS_BY_LABEL
from .project_io import MAX_PROJECT_BYTES, MAX_UNCOMPRESSED_BYTES, export_project, import_project


@dataclass
class Workspace:
    rooms: dict[str, Project] = field(default_factory=lambda: {"직접 설정": Project()})
    active: str = "직접 설정"

    @property
    def project(self) -> Project:
        return self.rooms[self.active]

    def open_room(self, key: str) -> Project:
        if key not in self.rooms:
            if key != "직접 설정" and key not in PRESETS_BY_LABEL:
                raise ValueError("알 수 없는 호실입니다.")
            project = Project()
            if key in PRESETS_BY_LABEL:
                PRESETS_BY_LABEL[key].apply(project)
            self.rooms[key] = project
        self.active = key
        return self.project


def download_name(workspace: Workspace, now: datetime | None = None) -> str:
    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    stamp = now.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S")
    prefix = workspace.active.split(" · ")[0] + "_" if " · " in workspace.active else ""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", workspace.project.room.name).strip(" .") or "공간"
    return f"{prefix}{name[:80]}_{stamp}.fplan"


def export_workspace(workspace: Workspace) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        entries = []
        for index, (key, project) in enumerate(workspace.rooms.items()):
            path = f"rooms/{index}.fplan"
            archive.writestr(path, export_project(project))
            entries.append({"key": key, "path": path})
        archive.writestr("workspace.json", json.dumps({"version": 2, "active": workspace.active,
                                                     "rooms": entries}, ensure_ascii=False))
    return output.getvalue()


def import_workspace(data: bytes) -> Workspace:
    if not data or len(data) > MAX_PROJECT_BYTES:
        raise ValueError("프로젝트 파일 크기가 올바르지 않습니다.")
    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("프로젝트가 너무 큽니다.")
            if "workspace.json" not in archive.namelist():
                project = import_project(data)
                key = next((label for label, preset in PRESETS_BY_LABEL.items()
                            if preset.image_file == project.plan_image_name), "직접 설정")
                return Workspace({key: project}, key)
            manifest = json.loads(archive.read("workspace.json"))
            if manifest["version"] != 2 or not 1 <= len(manifest["rooms"]) <= 24:
                raise ValueError("지원하지 않는 작업 파일입니다.")
            rooms = {}
            total = 0
            for index, entry in enumerate(manifest["rooms"]):
                key = entry["key"]
                if key in rooms or key not in {"직접 설정", *PRESETS_BY_LABEL}:
                    raise ValueError("호실 정보가 올바르지 않습니다.")
                if entry["path"] != f"rooms/{index}.fplan":
                    raise ValueError("호실 파일 경로가 올바르지 않습니다.")
                blob = archive.read(entry["path"])
                with ZipFile(BytesIO(blob)) as inner:
                    total += sum(i.file_size for i in inner.infolist())
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise ValueError("프로젝트가 너무 큽니다.")
                rooms[key] = import_project(blob)
            active = manifest["active"]
            if active not in rooms:
                raise ValueError("현재 호실 정보가 없습니다.")
            return Workspace(rooms, active)
    except (BadZipFile, KeyError, TypeError, AttributeError, UnicodeDecodeError) as exc:
        raise ValueError("올바른 .fplan 작업 파일이 아닙니다.") from exc
