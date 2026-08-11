from __future__ import annotations

import asyncio
import json
import mimetypes
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .auth import FirebaseAuth
from .errors import BundledNotesError
from .models import MAX_FILE_BYTES


class FirebaseStorage:
    def __init__(self, auth: FirebaseAuth, http: httpx.AsyncClient | None = None) -> None:
        self.auth = auth
        self.http = http or auth.http
        self.bucket = auth.settings.storage_bucket

    def object_url(self, object_name: str) -> str:
        return f"https://firebasestorage.googleapis.com/v0/b/{self.bucket}/o/{quote(object_name, safe='')}"

    async def upload(self, object_name: str, file_path: str, metadata: dict[str, str]) -> dict[str, Any]:
        path, size, payload = await asyncio.to_thread(_read_file, file_path)
        if size > MAX_FILE_BYTES:
            raise BundledNotesError("file_too_large", "Bundled Notes files are limited to 400 MiB.")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        boundary = f"bundled-notes-mcp-{secrets.token_hex(16)}"
        object_metadata = {"name": object_name, "contentType": content_type, "metadata": metadata}
        prefix = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(object_metadata, separators=(',', ':'))}\r\n"
            f"--{boundary}\r\nContent-Type: {content_type}\r\n\r\n"
        ).encode()
        body = prefix + payload + f"\r\n--{boundary}--\r\n".encode()
        headers = await self.auth.headers()
        headers["Content-Type"] = f"multipart/related; boundary={boundary}"
        headers["X-Goog-Upload-Protocol"] = "multipart"
        response = await self.http.post(
            f"https://firebasestorage.googleapis.com/v0/b/{self.bucket}/o",
            params={"name": object_name},
            content=body,
            headers=headers,
        )
        return _response(response)

    async def metadata(self, object_name: str, *, missing_ok: bool = False) -> dict[str, Any] | None:
        response = await self.http.get(self.object_url(object_name), headers=await self.auth.headers())
        if response.status_code == 404 and missing_ok:
            return None
        return _response(response)

    async def delete(self, object_name: str) -> None:
        response = await self.http.delete(self.object_url(object_name), headers=await self.auth.headers())
        if response.status_code not in {200, 204, 404}:
            _response(response)


def _response(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code >= 400:
        raise BundledNotesError(
            "storage_error", "Bundled Notes storage request failed.", status_code=response.status_code
        )
    return data if isinstance(data, dict) else {}


def _read_file(file_path: str) -> tuple[Path, int, bytes]:
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise BundledNotesError("file_not_found", "The local attachment file does not exist.")
    size = path.stat().st_size
    return path, size, path.read_bytes()
