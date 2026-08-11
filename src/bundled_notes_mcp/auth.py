from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import WEB_ORIGIN, Settings
from .errors import BundledNotesError


@dataclass(slots=True)
class Token:
    id_token: str
    refresh_token: str
    uid: str
    expires_at: float


class FirebaseAuth:
    """Refresh Firebase ID tokens without persisting secrets."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.http = http or httpx.AsyncClient(timeout=settings.timeout_seconds)
        self._token: Token | None = None
        self._lock = asyncio.Lock()

    @property
    def browser_headers(self) -> dict[str, str]:
        return {"Origin": WEB_ORIGIN, "Referer": f"{WEB_ORIGIN}/"}

    async def token(self) -> Token:
        if self._token and self._token.expires_at > time.time() + 60:
            return self._token
        async with self._lock:
            if self._token and self._token.expires_at > time.time() + 60:
                return self._token
            response = await self.http.post(
                "https://securetoken.googleapis.com/v1/token",
                params={"key": self.settings.api_key},
                data={"grant_type": "refresh_token", "refresh_token": self.settings.refresh_token},
                headers=self.browser_headers,
            )
            data = _json(response)
            if response.status_code >= 400:
                raise _auth_error(response.status_code, data)
            token = Token(
                id_token=str(data["id_token"]),
                refresh_token=str(data.get("refresh_token") or self.settings.refresh_token),
                uid=str(data["user_id"]),
                expires_at=time.time() + int(data.get("expires_in", 3600)),
            )
            if self.settings.expected_uid and token.uid != self.settings.expected_uid:
                raise BundledNotesError("uid_mismatch", "The refreshed token belongs to a different Firebase user.")
            self._token = token
            return token

    async def headers(self) -> dict[str, str]:
        token = await self.token()
        return {**self.browser_headers, "Authorization": f"Bearer {token.id_token}"}

    async def close(self) -> None:
        await self.http.aclose()


async def sign_in_with_password(api_key: str, email: str, password: str, http: httpx.AsyncClient) -> dict[str, str]:
    response = await http.post(
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
        params={"key": api_key},
        json={"email": email, "password": password, "returnSecureToken": True},
        headers={"Origin": WEB_ORIGIN, "Referer": f"{WEB_ORIGIN}/"},
    )
    data = _json(response)
    if response.status_code >= 400:
        raise _auth_error(response.status_code, data)
    return {"refresh_token": str(data["refreshToken"]), "uid": str(data["localId"])}


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _auth_error(status: int, data: dict[str, Any]) -> BundledNotesError:
    raw = data.get("error", {})
    reason = raw.get("message") if isinstance(raw, dict) else None
    safe = {
        "INVALID_PASSWORD": "The email or password was rejected.",
        "EMAIL_NOT_FOUND": "The email or password was rejected.",
        "INVALID_LOGIN_CREDENTIALS": "The email or password was rejected.",
        "TOKEN_EXPIRED": "The refresh token expired. Run the bootstrap command again.",
        "INVALID_REFRESH_TOKEN": "The refresh token is invalid. Run the bootstrap command again.",
        "PROJECT_NUMBER_MISMATCH": "The Firebase key and refresh token do not belong to the same project.",
    }.get(str(reason), "Firebase authentication failed.")
    return BundledNotesError("authentication_failed", safe, status_code=status)
