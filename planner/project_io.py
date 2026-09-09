from __future__ import annotations

import json
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from .models import Project


MAX_PROJECT_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 40 * 1024 * 1024


def export_project(project: Project) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "project.json",
            json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
        )
        if project.plan_image_bytes:
            archive.writestr("plan.bin", project.plan_image_bytes)
    return output.getvalue()


def import_project(data: bytes) -> Project:
    if not data or len(data) > MAX_PROJECT_BYTES:
        raise ValueError("프로젝트 파일 크기가 올바르지 않습니다.")
    try:
        with ZipFile(BytesIO(data), "r") as archive:
            infos = archive.infolist()
            if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("압축을 푼 프로젝트가 너무 큽니다.")
            for info in infos:
                path = PurePosixPath(info.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("안전하지 않은 프로젝트 경로입니다.")
            payload = json.loads(archive.read("project.json").decode("utf-8"))
            project = Project.from_dict(payload)
            if "plan.bin" in archive.namelist():
                project.plan_image_bytes = archive.read("plan.bin")
            return project
    except (BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("올바른 .fplan 프로젝트 파일이 아닙니다.") from exc
