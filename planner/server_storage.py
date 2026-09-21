"""Public, revision-checked workspace storage through the Supabase Data API."""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from json import JSONDecodeError, dumps, loads
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .project_io import MAX_PROJECT_BYTES
from .workspace import import_workspace


TABLE = "floorplan_projects"
PROJECT_ID = "shared"
MAX_RESPONSE_BYTES = (MAX_PROJECT_BYTES * 4 // 3) + 1024 * 1024


class ServerStorageError(RuntimeError):
    """The public workspace could not be read or saved."""


class ServerConflictError(ServerStorageError):
    """The server changed since this browser loaded its workspace."""


@dataclass(frozen=True, slots=True)
class ServerRecord:
    data: bytes
    revision: int
    updated_at: str


class SupabaseWorkspaceStore:
    def __init__(
        self,
        url: str,
        publishable_key: str,
        *,
        opener: Callable = urlopen,
        timeout: float = 10.0,
    ) -> None:
        if not isinstance(url, str):
            raise ServerStorageError("Supabase 주소가 올바르지 않습니다.")
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".supabase.co")
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ServerStorageError("Supabase 주소가 올바르지 않습니다.")
        if (
            not isinstance(publishable_key, str)
            or not publishable_key.strip().startswith("sb_publishable_")
        ):
            raise ServerStorageError("Supabase 공개 키가 올바르지 않습니다.")
        self.base_url = url.rstrip("/")
        self.publishable_key = publishable_key.strip()
        self.opener = opener
        self.timeout = timeout

    def _request(self, method: str, query: dict[str, str], body: dict | None = None) -> list:
        encoded = urlencode(query, safe=".*")
        request = Request(
            f"{self.base_url}/rest/v1/{TABLE}?{encoded}",
            data=None if body is None else dumps(body, separators=(",", ":")).encode("utf-8"),
            headers={
                "apikey": self.publishable_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            method=method,
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            if exc.code in (409, 412):
                raise ServerConflictError("다른 사용자가 먼저 서버 배치를 저장했습니다.") from exc
            raise ServerStorageError(f"서버 요청에 실패했습니다. (HTTP {exc.code})") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ServerStorageError("Supabase 서버에 연결하지 못했습니다.") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ServerStorageError("서버 배치 데이터가 너무 큽니다.")
        try:
            payload = loads(raw.decode("utf-8")) if raw else []
        except (UnicodeDecodeError, JSONDecodeError) as exc:
            raise ServerStorageError("서버 응답 형식이 올바르지 않습니다.") from exc
        if not isinstance(payload, list):
            raise ServerStorageError("서버 응답 형식이 올바르지 않습니다.")
        return payload

    def _rows(self, select: str) -> list:
        return self._request("GET", {
            "project_id": f"eq.{PROJECT_ID}",
            "select": select,
            "limit": "1",
        })

    @staticmethod
    def _revision(row: dict) -> int:
        if not isinstance(row, dict):
            raise ServerStorageError("서버 배치 버전이 올바르지 않습니다.")
        revision = row.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ServerStorageError("서버 배치 버전이 올바르지 않습니다.")
        return revision

    def load(self) -> ServerRecord | None:
        rows = self._rows("payload_base64,revision,updated_at")
        if not rows:
            return None
        row = rows[0]
        if not isinstance(row, dict) or not isinstance(row.get("payload_base64"), str):
            raise ServerStorageError("서버 배치 데이터가 올바르지 않습니다.")
        try:
            data = b64decode(row["payload_base64"], validate=True)
            import_workspace(data)
        except (ValueError, TypeError) as exc:
            raise ServerStorageError("서버 배치 파일이 손상되었습니다.") from exc
        updated_at = row.get("updated_at")
        if not isinstance(updated_at, str):
            updated_at = ""
        return ServerRecord(data, self._revision(row), updated_at)

    def save(self, data: bytes, expected_revision: int | None) -> ServerRecord:
        try:
            import_workspace(data)
        except ValueError as exc:
            raise ServerStorageError("저장할 프로젝트 데이터가 올바르지 않습니다.") from exc
        rows = self._rows("revision")
        encoded = b64encode(data).decode("ascii")
        if not rows:
            if expected_revision is not None:
                raise ServerConflictError("서버 배치가 변경되었습니다. 최신 내용을 다시 불러오세요.")
            result = self._request("POST", {}, {
                "project_id": PROJECT_ID,
                "payload_base64": encoded,
                "revision": 1,
            })
        else:
            current = self._revision(rows[0])
            if expected_revision != current:
                raise ServerConflictError("다른 사용자가 먼저 저장했습니다. 최신 내용을 다시 불러오세요.")
            result = self._request("PATCH", {
                "project_id": f"eq.{PROJECT_ID}",
                "revision": f"eq.{current}",
            }, {
                "payload_base64": encoded,
                "revision": current + 1,
            })
        if len(result) != 1:
            raise ServerConflictError("다른 사용자가 먼저 저장했습니다. 최신 내용을 다시 불러오세요.")
        row = result[0]
        return ServerRecord(data, self._revision(row), str(row.get("updated_at", "")))
