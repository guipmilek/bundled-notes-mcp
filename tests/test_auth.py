from __future__ import annotations

import time

import httpx
import pytest

from bundled_notes_mcp.auth import FirebaseAuth, sign_in_with_password
from bundled_notes_mcp.bootstrap import discover_public_config
from bundled_notes_mcp.config import WEB_ORIGIN, Settings
from bundled_notes_mcp.errors import BundledNotesError


@pytest.mark.asyncio
async def test_refresh_uses_browser_origin_and_caches() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["origin"] == WEB_ORIGIN
        assert request.headers["referer"] == f"{WEB_ORIGIN}/"
        assert "refresh_token=refresh" in request.content.decode()
        return httpx.Response(
            200, json={"id_token": "id", "refresh_token": "next", "user_id": "uid", "expires_in": "3600"}
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    auth = FirebaseAuth(Settings(api_key="public", refresh_token="refresh", expected_uid="uid"), http)
    assert (await auth.token()).id_token == "id"
    assert (await auth.token()).expires_at > time.time()
    assert calls == 1
    assert (await auth.headers())["Authorization"] == "Bearer id"
    await http.aclose()


@pytest.mark.asyncio
async def test_uid_mismatch_fails_closed() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id_token": "id", "user_id": "wrong", "expires_in": "3600"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    auth = FirebaseAuth(Settings(api_key="public", refresh_token="refresh", expected_uid="expected"), http)
    with pytest.raises(BundledNotesError, match="different Firebase user"):
        await auth.token()
    await http.aclose()


@pytest.mark.asyncio
async def test_password_signin_does_not_echo_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["origin"] == WEB_ORIGIN
        return httpx.Response(200, json={"refreshToken": "safe-result", "localId": "uid", "idToken": "ignored"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await sign_in_with_password("public", "person@example.com", "password", http)
    assert result == {"refresh_token": "safe-result", "uid": "uid"}


@pytest.mark.asyncio
async def test_bad_login_is_generic() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "INVALID_LOGIN_CREDENTIALS"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(BundledNotesError) as raised:
            await sign_in_with_password("public", "person@example.com", "wrong", http)
    assert raised.value.code == "authentication_failed"
    assert "person@example.com" not in raised.value.message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "asset",
    [
        'const firebase={apiKey:"public-key",projectId:"project",storageBucket:"bucket"}',
        "const env={VITE_APP_FIREBASE_API_KEY:`public-key`,VITE_APP_FIREBASE_PROJECT_ID:`project`,"
        "VITE_APP_FIREBASE_STORAGE_BUCKET:`bucket`}",
    ],
)
async def test_public_config_discovery_from_current_asset_shape(asset: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            return httpx.Response(200, text='<html><script src="/assets/app.js"></script></html>')
        return httpx.Response(200, text=asset)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        config = await discover_public_config(http)
    assert config == {"api_key": "public-key", "project_id": "project", "storage_bucket": "bucket"}


@pytest.mark.asyncio
async def test_public_config_discovery_failure_is_actionable() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html/>"))) as http:
        with pytest.raises(BundledNotesError) as raised:
            await discover_public_config(http)
    assert raised.value.code == "config_discovery_failed"
