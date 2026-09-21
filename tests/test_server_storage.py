import json
from urllib.error import HTTPError

import pytest

from planner.server_storage import (
    ServerConflictError,
    ServerStorageError,
    SupabaseWorkspaceStore,
)
from planner.workspace import Workspace, export_workspace, import_workspace


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit):
        return self.payload[:limit]


class Opener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return Response(response)


def store(opener):
    return SupabaseWorkspaceStore(
        "https://school.supabase.co", "sb_publishable_test", opener=opener,
    )


def encoded_workspace():
    data = export_workspace(Workspace())
    import base64
    return data, base64.b64encode(data).decode()


def test_load_validates_and_returns_workspace_archive():
    data, encoded = encoded_workspace()
    opener = Opener([{"payload_base64": encoded, "revision": 3, "updated_at": "now"}])

    record = store(opener).load()

    assert record.data == data
    assert record.revision == 3
    assert import_workspace(record.data).active == "직접 설정"
    request, timeout = opener.requests[0]
    assert request.get_header("Apikey") == "sb_publishable_test"
    assert request.method == "GET"
    assert timeout == 10


def test_first_save_inserts_revision_one():
    data, _ = encoded_workspace()
    opener = Opener([], [{"revision": 1, "updated_at": "created"}])

    record = store(opener).save(data, None)

    assert record.revision == 1
    assert [request.method for request, _ in opener.requests] == ["GET", "POST"]
    body = json.loads(opener.requests[1][0].data)
    assert body["project_id"] == "shared"
    assert body["revision"] == 1


def test_matching_revision_updates_with_compare_and_swap():
    data, _ = encoded_workspace()
    opener = Opener([{"revision": 4}], [{"revision": 5, "updated_at": "updated"}])

    record = store(opener).save(data, 4)

    assert record.revision == 5
    request = opener.requests[1][0]
    assert request.method == "PATCH"
    assert "revision=eq.4" in request.full_url
    assert json.loads(request.data)["revision"] == 5


def test_stale_or_empty_update_is_reported_as_conflict():
    data, _ = encoded_workspace()
    with pytest.raises(ServerConflictError):
        store(Opener([{"revision": 2}])).save(data, 1)
    with pytest.raises(ServerConflictError):
        store(Opener([{"revision": 2}], [])).save(data, 2)


def test_invalid_remote_payload_and_http_failure_are_safe_errors():
    with pytest.raises(ServerStorageError):
        store(Opener([{"payload_base64": "not-base64", "revision": 1}])).load()
    failure = HTTPError("https://school.supabase.co", 500, "error", {}, None)
    with pytest.raises(ServerStorageError, match="HTTP 500"):
        store(Opener(failure)).load()


@pytest.mark.parametrize("url", ["http://school.supabase.co", "not-a-url"])
def test_rejects_unsafe_supabase_url(url):
    with pytest.raises(ServerStorageError):
        SupabaseWorkspaceStore(url, "sb_publishable_test")


def test_rejects_secret_key():
    with pytest.raises(ServerStorageError):
        SupabaseWorkspaceStore("https://school.supabase.co", "sb_secret_do_not_use")
