from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from .auth import FirebaseAuth
from .errors import BundledNotesError


def encode_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return {"timestampValue": value.isoformat().replace("+00:00", "Z")}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, bytes):
        import base64

        return {"bytesValue": base64.b64encode(value).decode("ascii")}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [encode_value(item) for item in value]}}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {str(key): encode_value(item) for key, item in value.items()}}}
    raise TypeError(f"Unsupported Firestore value: {type(value).__name__}")


def decode_value(value: dict[str, Any]) -> Any:
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "stringValue" in value:
        return value["stringValue"]
    if "bytesValue" in value:
        return value["bytesValue"]
    if "referenceValue" in value:
        return value["referenceValue"]
    if "geoPointValue" in value:
        return value["geoPointValue"]
    if "arrayValue" in value:
        return [decode_value(item) for item in value["arrayValue"].get("values", [])]
    if "mapValue" in value:
        return {key: decode_value(item) for key, item in value["mapValue"].get("fields", {}).items()}
    return None


def encode_document(fields: dict[str, Any]) -> dict[str, Any]:
    return {"fields": {key: encode_value(value) for key, value in fields.items()}}


def decode_document(raw: dict[str, Any]) -> dict[str, Any]:
    value = {key: decode_value(field) for key, field in raw.get("fields", {}).items()}
    if raw.get("name"):
        value["_path"] = raw["name"].split("/documents/", 1)[-1]
    if raw.get("createTime"):
        value["_create_time"] = raw["createTime"]
    if raw.get("updateTime"):
        value["_update_time"] = raw["updateTime"]
    return value


class Firestore:
    def __init__(self, auth: FirebaseAuth, http: httpx.AsyncClient | None = None) -> None:
        self.auth = auth
        self.http = http or auth.http
        self.base = (
            f"https://firestore.googleapis.com/v1/projects/{auth.settings.project_id}/databases/(default)/documents"
        )

    def url(self, path: str) -> str:
        return f"{self.base}/{quote(path.strip('/'), safe='/')}"

    async def get(self, path: str, *, missing_ok: bool = False) -> dict[str, Any] | None:
        response = await self.http.get(self.url(path), headers=await self.auth.headers())
        if response.status_code == 404 and missing_ok:
            return None
        data = _response(response)
        return decode_document(data)

    async def list(self, path: str, *, page_size: int = 300) -> list[dict[str, Any]]:
        if page_size < 1 or page_size > 1000:
            raise BundledNotesError("invalid_page_size", "page_size must be between 1 and 1000.")
        url = self.url(path)
        token: str | None = None
        items: list[dict[str, Any]] = []
        while True:
            params: dict[str, Any] = {"pageSize": min(page_size, 300)}
            if token:
                params["pageToken"] = token
            response = await self.http.get(url, params=params, headers=await self.auth.headers())
            data = _response(response)
            items.extend(decode_document(raw) for raw in data.get("documents", []))
            token = data.get("nextPageToken")
            if not token or len(items) >= page_size:
                return items[:page_size]

    async def create(self, collection: str, document_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        response = await self.http.post(
            self.url(collection),
            params={"documentId": document_id},
            json=encode_document(fields),
            headers=await self.auth.headers(),
        )
        return decode_document(_response(response))

    async def patch(self, path: str, fields: dict[str, Any]) -> dict[str, Any]:
        if not fields:
            raise BundledNotesError("empty_update", "At least one field is required.")
        params = [("updateMask.fieldPaths", key) for key in fields]
        response = await self.http.patch(
            self.url(path), params=params, json=encode_document(fields), headers=await self.auth.headers()
        )
        return decode_document(_response(response))

    async def delete(self, path: str) -> None:
        response = await self.http.delete(self.url(path), headers=await self.auth.headers())
        if response.status_code not in {200, 404}:
            _response(response)


def _response(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code >= 400:
        raw = data.get("error", {}) if isinstance(data, dict) else {}
        status = raw.get("status") if isinstance(raw, dict) else None
        mapping = {401: "authentication_failed", 403: "permission_denied", 404: "not_found", 409: "conflict"}
        message = {
            401: "Authentication failed.",
            403: "Firebase security rules denied this operation.",
            404: "The requested Bundled Notes document was not found.",
            409: "A Bundled Notes document with this ID already exists.",
        }.get(response.status_code, "Bundled Notes Firestore request failed.")
        raise BundledNotesError(
            mapping.get(response.status_code, "firestore_error"),
            message,
            status_code=response.status_code,
            details={"firebase_status": status} if status else None,
        )
    return data if isinstance(data, dict) else {}
