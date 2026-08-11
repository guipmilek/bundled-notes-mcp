from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from bundled_notes_mcp.errors import BundledNotesError
from bundled_notes_mcp.firestore import _response, decode_document, decode_value, encode_document, encode_value


@pytest.mark.parametrize(
    "value",
    [None, True, False, 0, 42, -17, 1.5, "markdown", [], [1, "x", False], {}, {"a": 1, "b": [None]}],
)
def test_value_roundtrip(value: object) -> None:
    assert decode_value(encode_value(value)) == value


def test_timestamp_encoding() -> None:
    result = encode_value(datetime(2026, 8, 11, 12, 30, tzinfo=UTC))
    assert result == {"timestampValue": "2026-08-11T12:30:00Z"}


def test_document_metadata_decode() -> None:
    raw = {
        "name": "projects/x/databases/(default)/documents/users/u/bundles/b",
        "createTime": "2026-01-01T00:00:00Z",
        "updateTime": "2026-01-02T00:00:00Z",
        **encode_document({"id": "b", "name": "Bundle", "count": 2}),
    }
    value = decode_document(raw)
    assert value["id"] == "b"
    assert value["count"] == 2
    assert value["_path"] == "users/u/bundles/b"
    assert value["_create_time"].startswith("2026")


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "authentication_failed"), (403, "permission_denied"), (404, "not_found"), (409, "conflict")],
)
def test_http_errors_are_sanitized(status: int, code: str) -> None:
    response = httpx.Response(status, json={"error": {"status": "SENSITIVE_UPSTREAM", "message": "secret"}})
    with pytest.raises(BundledNotesError) as raised:
        _response(response)
    assert raised.value.code == code
    assert "secret" not in raised.value.message
    assert raised.value.details == {"firebase_status": "SENSITIVE_UPSTREAM"}


def test_unsupported_value_rejected() -> None:
    with pytest.raises(TypeError):
        encode_value(object())
