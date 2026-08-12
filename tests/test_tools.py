from __future__ import annotations

import asyncio

from bundled_notes_mcp.errors import BundledNotesError, public_error
from bundled_notes_mcp.server import mcp
from bundled_notes_mcp.tools import confirmation

EXPECTED_TOOLS = {
    "bundled_apply_tag",
    "bundled_apply_template",
    "bundled_configure_kanban",
    "bundled_create_bundle",
    "bundled_create_entry",
    "bundled_create_tag",
    "bundled_create_template",
    "bundled_current_user",
    "bundled_delete_account_attachment",
    "bundled_delete_bundle",
    "bundled_delete_entry",
    "bundled_delete_tag",
    "bundled_delete_template",
    "bundled_duplicate_entry",
    "bundled_download_attachment",
    "bundled_export_data",
    "bundled_get_bundle",
    "bundled_get_entry",
    "bundled_list_attachments",
    "bundled_list_bundles",
    "bundled_list_entries",
    "bundled_list_global_tags",
    "bundled_list_reminders",
    "bundled_list_tags",
    "bundled_list_templates",
    "bundled_move_entry",
    "bundled_move_kanban_entry",
    "bundled_remove_attachment",
    "bundled_remove_tag",
    "bundled_reorder_bundles",
    "bundled_reorder_entries",
    "bundled_reorder_tags",
    "bundled_refresh_link_previews",
    "bundled_search_entries",
    "bundled_schema_status",
    "bundled_set_bundle_archived",
    "bundled_set_entry_state",
    "bundled_set_global_tag_subscription",
    "bundled_status",
    "bundled_update_bundle",
    "bundled_update_entry",
    "bundled_update_tag",
    "bundled_upload_attachment",
}


def test_confirmation_contract() -> None:
    result = confirmation("delete_entry", {"entry_id": "e"})
    assert result["status"] == "confirmation_required"
    assert result["api_called"] is False
    assert result["summary"] == {"entry_id": "e"}


def test_unknown_errors_are_masked() -> None:
    assert public_error(RuntimeError("token=secret")) == {
        "code": "unexpected_error",
        "message": "Unexpected Bundled Notes MCP error.",
    }


def test_known_errors_keep_only_public_fields() -> None:
    value = public_error(BundledNotesError("tag_in_use", "Still referenced", details={"entry_ids": ["e"]}))
    assert value == {"code": "tag_in_use", "message": "Still referenced", "details": {"entry_ids": ["e"]}}


def test_tool_catalog_and_annotations() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert names == EXPECTED_TOOLS
    delete = next(tool for tool in tools if tool.name == "bundled_delete_bundle")
    read = next(tool for tool in tools if tool.name == "bundled_list_bundles")
    assert delete.annotations.destructiveHint is True
    assert read.annotations.readOnlyHint is True
