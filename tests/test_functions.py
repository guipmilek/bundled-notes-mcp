from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from bundled_notes_mcp.functions import FirebaseFunctions


class FakeAuth:
    settings = SimpleNamespace(project_id="project")

    async def headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer test"}


@pytest.mark.asyncio
async def test_callable_function_uses_firebase_wire_contract() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"result": {"ok": True}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await FirebaseFunctions(FakeAuth(), http).call("buildRichPreviewsForEntry", {"entryId": "e"})  # type: ignore[arg-type]

    request = captured["request"]
    assert isinstance(request, httpx.Request)
    assert str(request.url) == "https://us-central1-project.cloudfunctions.net/buildRichPreviewsForEntry"
    assert request.headers["Authorization"] == "Bearer test"
    assert request.content == b'{"data":{"entryId":"e"}}'
    assert result == {"ok": True}
