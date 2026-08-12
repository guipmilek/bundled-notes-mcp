from __future__ import annotations

from typing import Any

import httpx

from .auth import FirebaseAuth
from .errors import BundledNotesError


class FirebaseFunctions:
    """Minimal authenticated Firebase callable-functions transport."""

    def __init__(self, auth: FirebaseAuth, http: httpx.AsyncClient | None = None) -> None:
        self.auth = auth
        self.http = http or auth.http

    async def call(self, name: str, data: dict[str, Any]) -> Any:
        project_id = self.auth.settings.project_id
        response = await self.http.post(
            f"https://us-central1-{project_id}.cloudfunctions.net/{name}",
            json={"data": data},
            headers=await self.auth.headers(),
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("error")):
            raise BundledNotesError(
                "function_error",
                "The Bundled Notes callable function failed.",
                status_code=response.status_code,
            )
        if not isinstance(payload, dict):
            return None
        return payload.get("result", payload.get("data"))
