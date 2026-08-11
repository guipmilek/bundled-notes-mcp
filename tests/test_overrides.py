from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client, FastMCP

from bundled_notes_mcp.overrides import register_tool_overrides
from bundled_notes_mcp.tools import register_tools


class FakeClient:
    def __init__(self) -> None:
        self.state_calls: list[tuple[str, str, str, bool]] = []
        self.deleted_attachments: list[str] = []
        self.uploads: list[tuple[str, str, str, bytes]] = []

    async def current_user(self) -> dict[str, Any]:
        return {"uid": "u", "numberOfBundles": 1, "numberOfArchivedBundles": 0}

    async def list_bundles(self, *, include_archived: bool = False, limit: int = 300) -> list[dict[str, Any]]:
        rows = [
            {"id": "b1", "archived": False},
            {"id": "b2", "archived": False},
            {"id": "b3", "archived": True},
        ]
        return rows if include_archived else [row for row in rows if not row["archived"]]

    async def list_entries(
        self, bundle_id: str, *, include_archived: bool = False, limit: int = 300
    ) -> list[dict[str, Any]]:
        if bundle_id == "b1":
            return [{"id": "e1", "attachments": {"a1": {"text": "fixture.txt"}}}]
        return []

    async def set_entry_state(self, bundle_id: str, entry_id: str, field: str, value: bool) -> dict[str, Any]:
        self.state_calls.append((bundle_id, entry_id, field, value))
        return {"id": entry_id, field: value}

    async def upload_attachment(self, bundle_id: str, entry_id: str, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        payload = await asyncio.to_thread(path.read_bytes)
        self.uploads.append((bundle_id, entry_id, path.name, payload))
        return {"attachment": {"id": "new", "text": path.name, "fileSize": len(payload)}}

    async def delete_account_attachment(self, attachment_id: str) -> dict[str, Any]:
        self.deleted_attachments.append(attachment_id)
        return {"deleted": True, "attachment_id": attachment_id}


@pytest.fixture
def fake() -> FakeClient:
    return FakeClient()


@pytest.fixture
def mcp(fake: FakeClient) -> FastMCP:
    server = FastMCP("override-tests")
    register_tools(server, fake)  # type: ignore[arg-type]
    register_tool_overrides(server, fake)  # type: ignore[arg-type]
    return server


@pytest.mark.asyncio
async def test_current_user_uses_live_bundle_counts(mcp: FastMCP) -> None:
    async with Client(mcp) as session:
        result = (await session.call_tool("bundled_current_user")).data
    assert result["numberOfBundles"] == 2
    assert result["numberOfArchivedBundles"] == 1
    assert result["reportedNumberOfBundles"] == 1
    assert result["reportedNumberOfArchivedBundles"] == 0
    assert result["bundleCountSource"] == "live_bundle_listing"


@pytest.mark.asyncio
async def test_marked_as_complete_alias_is_accepted(mcp: FastMCP, fake: FakeClient) -> None:
    args = {"bundle_id": "b1", "entry_id": "e1", "state": "markedAsComplete", "value": True, "confirm": True}
    async with Client(mcp) as session:
        result = (await session.call_tool("bundled_set_entry_state", args)).data
    assert result["markedAsComplete"] is True
    assert fake.state_calls == [("b1", "e1", "markedAsComplete", True)]


@pytest.mark.asyncio
async def test_remote_base64_upload_does_not_require_shared_filesystem(mcp: FastMCP, fake: FakeClient) -> None:
    encoded = base64.b64encode(b"remote fixture\n").decode("ascii")
    args = {
        "bundle_id": "b1",
        "entry_id": "e1",
        "filename": "folder/fixture.txt",
        "content_base64": encoded,
    }
    async with Client(mcp) as session:
        preview = (await session.call_tool("bundled_upload_attachment", args)).data
        uploaded = (await session.call_tool("bundled_upload_attachment", args | {"confirm": True})).data
    assert preview["status"] == "confirmation_required"
    assert preview["api_called"] is False
    assert preview["summary"] == {
        "bundle_id": "b1",
        "entry_id": "e1",
        "source": "inline_base64",
        "filename": "fixture.txt",
    }
    assert encoded not in str(preview)
    assert uploaded["attachment"]["text"] == "fixture.txt"
    assert fake.uploads == [("b1", "e1", "fixture.txt", b"remote fixture\n")]


@pytest.mark.asyncio
async def test_upload_requires_exactly_one_source(mcp: FastMCP) -> None:
    async with Client(mcp) as session:
        neither = (await session.call_tool("bundled_upload_attachment", {"bundle_id": "b1", "entry_id": "e1"})).data
        both = (
            await session.call_tool(
                "bundled_upload_attachment",
                {
                    "bundle_id": "b1",
                    "entry_id": "e1",
                    "file_path": "/tmp/a.txt",
                    "filename": "a.txt",
                    "content_base64": "YQ==",
                },
            )
        ).data
    assert neither["error"]["code"] == "invalid_attachment_source"
    assert both["error"]["code"] == "invalid_attachment_source"


@pytest.mark.asyncio
async def test_account_attachment_delete_refuses_dangling_reference(mcp: FastMCP, fake: FakeClient) -> None:
    async with Client(mcp) as session:
        blocked = (
            await session.call_tool("bundled_delete_account_attachment", {"attachment_id": "a1", "confirm": True})
        ).data
        allowed = (
            await session.call_tool(
                "bundled_delete_account_attachment",
                {"attachment_id": "a1", "allow_dangling_references": True, "confirm": True},
            )
        ).data
    assert blocked["status"] == "error"
    assert blocked["error"]["code"] == "attachment_in_use"
    assert blocked["error"]["details"] == {"entry_ids_by_bundle": {"b1": ["e1"]}}
    assert fake.deleted_attachments == ["a1"]
    assert allowed["dangling_entry_ids_by_bundle"] == {"b1": ["e1"]}
