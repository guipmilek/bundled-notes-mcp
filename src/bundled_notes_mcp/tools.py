from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import __version__
from .auth import FirebaseAuth
from .client import BundledNotesClient
from .config import Settings
from .errors import BundledNotesError, public_error
from .models import BundleCreate, BundleUpdate, EntryCreate, EntryUpdate, TagCreate, TagUpdate

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
CREATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False)
DELETE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False)


@lru_cache(maxsize=1)
def default_client() -> BundledNotesClient:
    return BundledNotesClient(FirebaseAuth(Settings.from_env()))


def confirmation(operation: str, summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "confirmation_required",
        "api_called": False,
        "operation": operation,
        "summary": summary,
        "next_step": "Review identifiers and payload, then call again with confirm=true.",
    }


async def attempt(call: Callable[[], Awaitable[Any]]) -> Any:
    try:
        return await call()
    except Exception as error:
        return {"status": "error", "error": public_error(error)}


async def collection(key: str, call: Awaitable[list[dict[str, Any]]]) -> dict[str, Any]:
    items = await call
    return {key: items, "count": len(items)}


def register_tools(mcp: FastMCP, api: BundledNotesClient | None = None) -> None:
    def client() -> BundledNotesClient:
        return api or default_client()

    @mcp.tool(name="bundled_status", title="Bundled Notes MCP Status", annotations=READ_ONLY)
    async def bundled_status() -> dict[str, Any]:
        """Report configuration and validate the Firebase refresh token with a real read."""
        try:
            current = await client().current_user()
            return {
                "server_version": __version__,
                "configured": True,
                "authenticated": True,
                "uid": current.get("uid"),
                "project_id": client().auth.settings.project_id,
            }
        except BundledNotesError as error:
            return {
                "server_version": __version__,
                "configured": error.code != "not_configured",
                "authenticated": False,
                "error": error.public(),
            }

    @mcp.tool(name="bundled_current_user", title="Get Bundled Notes Account", annotations=READ_ONLY)
    async def bundled_current_user() -> dict[str, Any]:
        """Return a safe account projection; purchase and authentication tokens are always omitted."""
        return await attempt(lambda: client().current_user())

    @mcp.tool(name="bundled_list_bundles", title="List Bundles", annotations=READ_ONLY)
    async def bundled_list_bundles(include_archived: bool = False, limit: int = 300) -> Any:
        """List bundles, optionally including archived bundles."""
        return await attempt(
            lambda: collection("bundles", client().list_bundles(include_archived=include_archived, limit=limit))
        )

    @mcp.tool(name="bundled_get_bundle", title="Get Bundle", annotations=READ_ONLY)
    async def bundled_get_bundle(bundle_id: str) -> Any:
        """Get one bundle and all known presentation/Kanban settings."""
        return await attempt(lambda: client().get_bundle(bundle_id))

    @mcp.tool(name="bundled_create_bundle", title="Create Bundle", annotations=CREATE)
    async def bundled_create_bundle(spec: BundleCreate, confirm: bool = False) -> Any:
        """Create a Notes, List, or Board bundle. Requires confirm=true."""
        if not confirm:
            return confirmation("create_bundle", spec.model_dump())
        return await attempt(lambda: client().create_bundle(spec))

    @mcp.tool(name="bundled_update_bundle", title="Update Bundle", annotations=UPDATE)
    async def bundled_update_bundle(bundle_id: str, spec: BundleUpdate, confirm: bool = False) -> Any:
        """Partially update bundle details, layout, sorting, or display settings."""
        if not confirm:
            return confirmation("update_bundle", {"bundle_id": bundle_id, **spec.model_dump(exclude_none=True)})
        return await attempt(lambda: client().update_bundle(bundle_id, spec))

    @mcp.tool(name="bundled_set_bundle_archived", title="Archive or Restore Bundle", annotations=UPDATE)
    async def bundled_set_bundle_archived(bundle_id: str, archived: bool, confirm: bool = False) -> Any:
        """Archive or restore a bundle without deleting its contents."""
        if not confirm:
            return confirmation("set_bundle_archived", {"bundle_id": bundle_id, "archived": archived})
        return await attempt(lambda: client().set_bundle_archived(bundle_id, archived))

    @mcp.tool(name="bundled_delete_bundle", title="Permanently Delete Bundle", annotations=DELETE)
    async def bundled_delete_bundle(bundle_id: str, confirm: bool = False) -> Any:
        """Permanently delete a bundle plus all entry and tag subdocuments."""
        if not confirm:
            return confirmation("delete_bundle_recursive", {"bundle_id": bundle_id, "permanent": True})
        return await attempt(lambda: client().delete_bundle(bundle_id))

    @mcp.tool(name="bundled_list_entries", title="List Bundle Entries", annotations=READ_ONLY)
    async def bundled_list_entries(bundle_id: str, include_archived: bool = False, limit: int = 300) -> Any:
        """List notes/entries in one bundle."""
        return await attempt(
            lambda: collection(
                "entries", client().list_entries(bundle_id, include_archived=include_archived, limit=limit)
            )
        )

    @mcp.tool(name="bundled_get_entry", title="Get Entry", annotations=READ_ONLY)
    async def bundled_get_entry(bundle_id: str, entry_id: str) -> Any:
        """Get an entry with Markdown content, tag IDs, state, and attachment metadata."""
        return await attempt(lambda: client().get_entry(bundle_id, entry_id))

    @mcp.tool(name="bundled_search_entries", title="Search Entries", annotations=READ_ONLY)
    async def bundled_search_entries(
        query: str,
        bundle_id: str | None = None,
        tag_id: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> Any:
        """Client-side text search matching the web app's local title/content search semantics."""
        return await attempt(
            lambda: collection(
                "matches",
                client().search(
                    query, bundle_id=bundle_id, tag_id=tag_id, include_archived=include_archived, limit=limit
                ),
            )
        )

    @mcp.tool(name="bundled_create_entry", title="Create Entry", annotations=CREATE)
    async def bundled_create_entry(bundle_id: str, spec: EntryCreate, confirm: bool = False) -> Any:
        """Create a Markdown entry in a bundle."""
        if not confirm:
            return confirmation("create_entry", {"bundle_id": bundle_id, **spec.model_dump()})
        return await attempt(lambda: client().create_entry(bundle_id, spec))

    @mcp.tool(name="bundled_update_entry", title="Update Entry", annotations=UPDATE)
    async def bundled_update_entry(bundle_id: str, entry_id: str, spec: EntryUpdate, confirm: bool = False) -> Any:
        """Partially update entry text, tags, or pin state."""
        if not confirm:
            return confirmation(
                "update_entry", {"bundle_id": bundle_id, "entry_id": entry_id, **spec.model_dump(exclude_none=True)}
            )
        return await attempt(lambda: client().update_entry(bundle_id, entry_id, spec))

    @mcp.tool(name="bundled_set_entry_state", title="Set Entry State", annotations=UPDATE)
    async def bundled_set_entry_state(
        bundle_id: str, entry_id: str, state: str, value: bool, confirm: bool = False
    ) -> Any:
        """Set archived, markedAsComplete, or pinned explicitly; never toggles blindly."""
        field = {"archived": "archived", "completed": "markedAsComplete", "pinned": "pinned"}.get(state)
        if field is None:
            return {
                "status": "error",
                "error": {"code": "invalid_state", "message": "state must be archived, completed, or pinned."},
            }
        if not confirm:
            return confirmation(
                "set_entry_state", {"bundle_id": bundle_id, "entry_id": entry_id, "state": state, "value": value}
            )
        return await attempt(lambda: client().set_entry_state(bundle_id, entry_id, field, value))

    @mcp.tool(name="bundled_delete_entry", title="Permanently Delete Entry", annotations=DELETE)
    async def bundled_delete_entry(bundle_id: str, entry_id: str, confirm: bool = False) -> Any:
        """Permanently delete one entry. Account-storage files are not deleted."""
        if not confirm:
            return confirmation("delete_entry", {"bundle_id": bundle_id, "entry_id": entry_id, "permanent": True})
        return await attempt(lambda: client().delete_entry(bundle_id, entry_id))

    @mcp.tool(name="bundled_duplicate_entry", title="Duplicate Entry", annotations=CREATE)
    async def bundled_duplicate_entry(
        source_bundle_id: str,
        entry_id: str,
        target_bundle_id: str,
        target_tag_ids: list[str] | None = None,
        confirm: bool = False,
    ) -> Any:
        """Copy an entry. The copy gets a new document and numeric ID; destination tags are explicit."""
        summary = {
            "source_bundle_id": source_bundle_id,
            "entry_id": entry_id,
            "target_bundle_id": target_bundle_id,
            "target_tag_ids": target_tag_ids or [],
        }
        if not confirm:
            return confirmation("duplicate_entry", summary)
        return await attempt(
            lambda: client().duplicate_entry(source_bundle_id, entry_id, target_bundle_id, target_tag_ids)
        )

    @mcp.tool(name="bundled_move_entry", title="Move Entry", annotations=UPDATE)
    async def bundled_move_entry(
        source_bundle_id: str,
        entry_id: str,
        target_bundle_id: str,
        target_tag_ids: list[str] | None = None,
        confirm: bool = False,
    ) -> Any:
        """Copy to the destination, verify it, then delete the source; rolls back the copy if source deletion fails."""
        summary = {
            "source_bundle_id": source_bundle_id,
            "entry_id": entry_id,
            "target_bundle_id": target_bundle_id,
            "target_tag_ids": target_tag_ids or [],
        }
        if not confirm:
            return confirmation("move_entry", summary)
        return await attempt(lambda: client().move_entry(source_bundle_id, entry_id, target_bundle_id, target_tag_ids))

    @mcp.tool(name="bundled_list_tags", title="List Bundle Tags", annotations=READ_ONLY)
    async def bundled_list_tags(bundle_id: str, include_global: bool = True) -> Any:
        """List bundle-local tags and subscribed global tags."""
        return await attempt(lambda: collection("tags", client().list_tags(bundle_id, include_global=include_global)))

    @mcp.tool(name="bundled_create_tag", title="Create Tag or Task", annotations=CREATE)
    async def bundled_create_tag(bundle_id: str, spec: TagCreate, confirm: bool = False) -> Any:
        """Create a local/global tag, optionally with completion, archive, or tag-swap task actions."""
        if not confirm:
            return confirmation("create_tag", {"bundle_id": bundle_id, **spec.model_dump()})
        return await attempt(lambda: client().create_tag(bundle_id, spec))

    @mcp.tool(name="bundled_update_tag", title="Update Tag or Task", annotations=UPDATE)
    async def bundled_update_tag(
        bundle_id: str, tag_id: str, spec: TagUpdate, global_tag: bool = False, confirm: bool = False
    ) -> Any:
        """Partially update a local or global tag definition."""
        if not confirm:
            return confirmation(
                "update_tag",
                {
                    "bundle_id": bundle_id,
                    "tag_id": tag_id,
                    "global_tag": global_tag,
                    **spec.model_dump(exclude_none=True),
                },
            )
        return await attempt(lambda: client().update_tag(bundle_id, tag_id, spec, global_tag=global_tag))

    @mcp.tool(name="bundled_apply_tag", title="Apply Tag", annotations=UPDATE)
    async def bundled_apply_tag(
        bundle_id: str, entry_id: str, tag_id: str, apply_actions: bool = False, confirm: bool = False
    ) -> Any:
        """Apply a tag; optionally execute its completion/archive/swap actions."""
        if not confirm:
            return confirmation(
                "apply_tag",
                {"bundle_id": bundle_id, "entry_id": entry_id, "tag_id": tag_id, "apply_actions": apply_actions},
            )
        return await attempt(lambda: client().apply_tag(bundle_id, entry_id, tag_id, apply_actions=apply_actions))

    @mcp.tool(name="bundled_remove_tag", title="Remove Tag", annotations=UPDATE)
    async def bundled_remove_tag(bundle_id: str, entry_id: str, tag_id: str, confirm: bool = False) -> Any:
        """Remove one tag reference from an entry."""
        if not confirm:
            return confirmation("remove_tag", {"bundle_id": bundle_id, "entry_id": entry_id, "tag_id": tag_id})
        return await attempt(lambda: client().remove_tag(bundle_id, entry_id, tag_id))

    @mcp.tool(name="bundled_delete_tag", title="Permanently Delete Tag", annotations=DELETE)
    async def bundled_delete_tag(
        bundle_id: str,
        tag_id: str,
        global_tag: bool = False,
        allow_dangling_references: bool = False,
        confirm: bool = False,
    ) -> Any:
        """Delete a tag. By default refuses when entries or Kanban still reference it."""
        summary = {
            "bundle_id": bundle_id,
            "tag_id": tag_id,
            "global_tag": global_tag,
            "allow_dangling_references": allow_dangling_references,
            "permanent": True,
        }
        if not confirm:
            return confirmation("delete_tag", summary)
        return await attempt(
            lambda: client().delete_tag(
                bundle_id, tag_id, global_tag=global_tag, allow_dangling_references=allow_dangling_references
            )
        )

    @mcp.tool(name="bundled_configure_kanban", title="Configure Kanban", annotations=UPDATE)
    async def bundled_configure_kanban(
        bundle_id: str,
        column_tag_ids: list[str],
        enabled: bool = True,
        backlog_name: str = "Backlog",
        hide_backlog_if_empty: bool = True,
        show_all_column: bool = False,
        confirm: bool = False,
    ) -> Any:
        """Enable/configure a board using ordered tag IDs as columns."""
        summary = {
            "bundle_id": bundle_id,
            "column_tag_ids": column_tag_ids,
            "enabled": enabled,
            "backlog_name": backlog_name,
            "hide_backlog_if_empty": hide_backlog_if_empty,
            "show_all_column": show_all_column,
        }
        if not confirm:
            return confirmation("configure_kanban", summary)
        return await attempt(
            lambda: client().configure_kanban(
                bundle_id,
                column_tag_ids,
                enabled=enabled,
                backlog_name=backlog_name,
                hide_backlog_if_empty=hide_backlog_if_empty,
                show_all_column=show_all_column,
            )
        )

    @mcp.tool(name="bundled_move_kanban_entry", title="Move Entry Across Kanban", annotations=UPDATE)
    async def bundled_move_kanban_entry(
        bundle_id: str, entry_id: str, target_column_tag_id: str | None, confirm: bool = False
    ) -> Any:
        """Move an entry to one configured column, or to backlog with null."""
        if not confirm:
            return confirmation(
                "move_kanban_entry",
                {"bundle_id": bundle_id, "entry_id": entry_id, "target_column_tag_id": target_column_tag_id},
            )
        return await attempt(lambda: client().move_kanban(bundle_id, entry_id, target_column_tag_id))

    @mcp.tool(name="bundled_list_templates", title="List Custom Templates", annotations=READ_ONLY)
    async def bundled_list_templates(limit: int = 300) -> Any:
        """List user-created bundle templates."""
        return await attempt(lambda: collection("templates", client().list_templates(limit)))

    @mcp.tool(name="bundled_create_template", title="Create Bundle Template", annotations=CREATE)
    async def bundled_create_template(
        bundle_id: str, name: str, description: str = "", include_entries: bool = False, confirm: bool = False
    ) -> Any:
        """Create a custom template from a bundle, copying local tags and optionally entries."""
        summary = {"bundle_id": bundle_id, "name": name, "description": description, "include_entries": include_entries}
        if not confirm:
            return confirmation("create_template", summary)
        return await attempt(lambda: client().create_template(bundle_id, name, description, include_entries))

    @mcp.tool(name="bundled_apply_template", title="Apply Bundle Template", annotations=CREATE)
    async def bundled_apply_template(
        template_id: str, name: str | None = None, default_bundle: bool = False, confirm: bool = False
    ) -> Any:
        """Create a new bundle from a custom template."""
        if not confirm:
            return confirmation(
                "apply_template", {"template_id": template_id, "name": name, "default_bundle": default_bundle}
            )
        return await attempt(lambda: client().apply_template(template_id, name=name, default_bundle=default_bundle))

    @mcp.tool(name="bundled_delete_template", title="Permanently Delete Template", annotations=DELETE)
    async def bundled_delete_template(template_id: str, confirm: bool = False) -> Any:
        """Permanently delete a custom template and its copied tags/entries."""
        if not confirm:
            return confirmation("delete_template_recursive", {"template_id": template_id, "permanent": True})
        return await attempt(lambda: client().delete_template(template_id))

    @mcp.tool(name="bundled_list_attachments", title="List Account Files", annotations=READ_ONLY)
    async def bundled_list_attachments(limit: int = 300) -> Any:
        """List account-level Files & Photos metadata without download tokens."""
        return await attempt(lambda: collection("attachments", client().list_attachments(limit)))

    @mcp.tool(name="bundled_upload_attachment", title="Upload and Attach File", annotations=CREATE)
    async def bundled_upload_attachment(bundle_id: str, entry_id: str, file_path: str, confirm: bool = False) -> Any:
        """Upload a local file to account storage and attach it to an entry (400 MiB maximum)."""
        if not confirm:
            return confirmation(
                "upload_attachment", {"bundle_id": bundle_id, "entry_id": entry_id, "file_path": file_path}
            )
        return await attempt(lambda: client().upload_attachment(bundle_id, entry_id, file_path))

    @mcp.tool(name="bundled_remove_attachment", title="Detach File from Entry", annotations=UPDATE)
    async def bundled_remove_attachment(
        bundle_id: str, entry_id: str, attachment_id: str, confirm: bool = False
    ) -> Any:
        """Remove an attachment reference from an entry but keep the account-storage file."""
        if not confirm:
            return confirmation(
                "remove_attachment",
                {
                    "bundle_id": bundle_id,
                    "entry_id": entry_id,
                    "attachment_id": attachment_id,
                    "keeps_account_file": True,
                },
            )
        return await attempt(lambda: client().remove_attachment(bundle_id, entry_id, attachment_id))

    @mcp.tool(name="bundled_delete_account_attachment", title="Delete Account File", annotations=DELETE)
    async def bundled_delete_account_attachment(attachment_id: str, confirm: bool = False) -> Any:
        """Permanently delete the account catalog record and storage object; detach references first."""
        if not confirm:
            return confirmation("delete_account_attachment", {"attachment_id": attachment_id, "permanent": True})
        return await attempt(lambda: client().delete_account_attachment(attachment_id))
