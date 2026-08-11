from __future__ import annotations

import base64
import binascii
import tempfile
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .client import BundledNotesClient
from .errors import BundledNotesError
from .models import MAX_FILE_BYTES
from .tools import CREATE, DELETE, READ_ONLY, UPDATE, attempt, confirmation, default_client


def register_tool_overrides(mcp: FastMCP, api: BundledNotesClient | None = None) -> None:
    """Replace tools whose remote-host semantics need stricter behavior."""

    def client() -> BundledNotesClient:
        return api or default_client()

    for name in (
        "bundled_current_user",
        "bundled_set_entry_state",
        "bundled_upload_attachment",
        "bundled_delete_account_attachment",
    ):
        mcp.local_provider.remove_tool(name)

    @mcp.tool(name="bundled_current_user", title="Get Bundled Notes Account", annotations=READ_ONLY)
    async def bundled_current_user() -> dict[str, Any]:
        """Return a safe account projection with bundle counts recalculated from live bundle documents."""

        async def read_account() -> dict[str, Any]:
            account = await client().current_user()
            bundles = await client().list_bundles(include_archived=True, limit=1000)
            actual_active = sum(not bool(bundle.get("archived", False)) for bundle in bundles)
            actual_archived = sum(bool(bundle.get("archived", False)) for bundle in bundles)

            reported_active = account.get("numberOfBundles")
            reported_archived = account.get("numberOfArchivedBundles")
            if reported_active != actual_active:
                account["reportedNumberOfBundles"] = reported_active
            if reported_archived != actual_archived:
                account["reportedNumberOfArchivedBundles"] = reported_archived

            account["numberOfBundles"] = actual_active
            account["numberOfArchivedBundles"] = actual_archived
            account["bundleCountSource"] = "live_bundle_listing"
            return account

        return await attempt(read_account)

    @mcp.tool(name="bundled_set_entry_state", title="Set Entry State", annotations=UPDATE)
    async def bundled_set_entry_state(
        bundle_id: str, entry_id: str, state: str, value: bool, confirm: bool = False
    ) -> Any:
        """Set archived, completed/markedAsComplete, or pinned explicitly; never toggles blindly."""
        field = {
            "archived": "archived",
            "completed": "markedAsComplete",
            "markedAsComplete": "markedAsComplete",
            "pinned": "pinned",
        }.get(state)
        if field is None:
            return {
                "status": "error",
                "error": {
                    "code": "invalid_state",
                    "message": "state must be archived, completed, markedAsComplete, or pinned.",
                },
            }
        if not confirm:
            return confirmation(
                "set_entry_state", {"bundle_id": bundle_id, "entry_id": entry_id, "state": state, "value": value}
            )
        return await attempt(lambda: client().set_entry_state(bundle_id, entry_id, field, value))

    @mcp.tool(name="bundled_upload_attachment", title="Upload and Attach File", annotations=CREATE)
    async def bundled_upload_attachment(
        bundle_id: str,
        entry_id: str,
        file_path: str | None = None,
        filename: str | None = None,
        content_base64: str | None = None,
        confirm: bool = False,
    ) -> Any:
        """Upload a file. Remote clients should send filename+content_base64; file_path is server-local only."""
        has_path = bool(file_path)
        has_inline = content_base64 is not None
        if has_path == has_inline:
            return {
                "status": "error",
                "error": {
                    "code": "invalid_attachment_source",
                    "message": "Provide exactly one source: file_path or content_base64.",
                },
            }

        if has_inline and not filename:
            return {
                "status": "error",
                "error": {
                    "code": "filename_required",
                    "message": "filename is required when content_base64 is used.",
                },
            }

        source = "inline_base64" if has_inline else "server_local_path"
        summary = {
            "bundle_id": bundle_id,
            "entry_id": entry_id,
            "source": source,
            "filename": _safe_filename(filename) if has_inline and filename else Path(file_path or "").name,
        }
        if not confirm:
            return confirmation("upload_attachment", summary)

        if has_path:
            return await attempt(lambda: client().upload_attachment(bundle_id, entry_id, file_path or ""))

        async def upload_inline() -> Any:
            payload = _decode_base64(content_base64 or "")
            safe_name = _safe_filename(filename or "")
            with tempfile.TemporaryDirectory(prefix="bundled-notes-mcp-upload-") as directory:
                path = Path(directory) / safe_name
                path.write_bytes(payload)
                return await client().upload_attachment(bundle_id, entry_id, str(path))

        return await attempt(upload_inline)

    @mcp.tool(name="bundled_delete_account_attachment", title="Delete Account File", annotations=DELETE)
    async def bundled_delete_account_attachment(
        attachment_id: str, allow_dangling_references: bool = False, confirm: bool = False
    ) -> Any:
        """Permanently delete an account file; refuses while entries still reference it unless explicitly allowed."""
        summary = {
            "attachment_id": attachment_id,
            "allow_dangling_references": allow_dangling_references,
            "permanent": True,
        }
        if not confirm:
            return confirmation("delete_account_attachment", summary)

        async def delete_checked() -> Any:
            references = await _find_attachment_references(client(), attachment_id)
            if references and not allow_dangling_references:
                raise BundledNotesError(
                    "attachment_in_use",
                    "The account file is still referenced by one or more entries; detach it first.",
                    details={"entry_ids_by_bundle": references},
                )
            deleted = await client().delete_account_attachment(attachment_id)
            if references:
                deleted["dangling_entry_ids_by_bundle"] = references
            return deleted

        return await attempt(delete_checked)


def _safe_filename(filename: str) -> str:
    safe = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not safe or safe in {".", ".."}:
        raise BundledNotesError("invalid_filename", "A valid attachment filename is required.")
    return safe


def _decode_base64(value: str) -> bytes:
    if len(value) > ((MAX_FILE_BYTES + 2) // 3) * 4:
        raise BundledNotesError("file_too_large", "Bundled Notes files are limited to 400 MiB.")
    try:
        payload = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise BundledNotesError("invalid_base64", "content_base64 is not valid base64 data.") from error
    if len(payload) > MAX_FILE_BYTES:
        raise BundledNotesError("file_too_large", "Bundled Notes files are limited to 400 MiB.")
    return payload


async def _find_attachment_references(api: BundledNotesClient, attachment_id: str) -> dict[str, list[str]]:
    references: dict[str, list[str]] = {}
    for bundle in await api.list_bundles(include_archived=True, limit=1000):
        entries = await api.list_entries(bundle["id"], include_archived=True, limit=1000)
        matches = [entry["id"] for entry in entries if attachment_id in (entry.get("attachments") or {})]
        if matches:
            references[bundle["id"]] = matches
    return references
