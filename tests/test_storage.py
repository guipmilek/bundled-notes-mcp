from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from bundled_notes_mcp.storage import FirebaseStorage


class FakeAuth:
    settings = SimpleNamespace(storage_bucket="bucket.example")

    async def headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer test"}


@pytest.mark.asyncio
async def test_multipart_upload_uses_firebase_protocol_and_preserves_raw_bytes(tmp_path) -> None:
    payload = b"hello\n"
    fixture = tmp_path / "fixture.txt"
    fixture.write_bytes(payload)
    custom = {"filename": "fixture.txt", "targetBundleId": "b", "targetEntryId": "e"}
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(
            200,
            json={
                "name": "users/u/a",
                "size": str(len(payload)),
                "contentType": "text/plain",
                "metadata": custom,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await FirebaseStorage(FakeAuth(), http).upload("users/u/a", str(fixture), custom)  # type: ignore[arg-type]

    request = captured["request"]
    assert isinstance(request, httpx.Request)
    assert request.headers["X-Goog-Upload-Protocol"] == "multipart"
    assert request.url.params["name"] == "users/u/a"
    assert "uploadType" not in request.url.params
    content_type = request.headers["Content-Type"]
    boundary = content_type.split("boundary=", 1)[1]
    prefix, uploaded_bytes = request.content.split(f"\r\n--{boundary}\r\nContent-Type: text/plain\r\n\r\n".encode(), 1)
    metadata_json = prefix.split(b"\r\n\r\n", 1)[1]
    assert json.loads(metadata_json) == {
        "name": "users/u/a",
        "contentType": "text/plain",
        "metadata": custom,
    }
    assert uploaded_bytes == payload + f"\r\n--{boundary}--\r\n".encode()
    assert result["size"] == str(len(payload))
