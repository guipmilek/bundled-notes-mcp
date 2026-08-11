from __future__ import annotations

import argparse
import asyncio
import base64
import json
from typing import Any

from fastmcp import Client

from bundled_notes_mcp.server import mcp

MUTATING_TOOLS = {
    "bundled_apply_tag",
    "bundled_apply_template",
    "bundled_configure_kanban",
    "bundled_create_bundle",
    "bundled_create_entry",
    "bundled_create_tag",
    "bundled_create_template",
    "bundled_delete_account_attachment",
    "bundled_delete_bundle",
    "bundled_delete_entry",
    "bundled_delete_tag",
    "bundled_delete_template",
    "bundled_duplicate_entry",
    "bundled_move_entry",
    "bundled_move_kanban_entry",
    "bundled_remove_attachment",
    "bundled_remove_tag",
    "bundled_set_bundle_archived",
    "bundled_set_entry_state",
    "bundled_update_bundle",
    "bundled_update_entry",
    "bundled_update_tag",
    "bundled_upload_attachment",
}


async def run(run_id: str) -> dict[str, Any]:
    prefix = f"[MCP TEST {run_id}]"
    bundle_ids: list[str] = []
    template_ids: list[str] = []
    account_attachment_ids: list[str] = []
    global_tags: list[tuple[str, str]] = []
    checks: list[str] = []
    called_tools: set[str] = set()

    async with Client(mcp, timeout=60) as session:

        async def call(name: str, arguments: dict[str, Any] | None = None) -> Any:
            payload = dict(arguments or {})
            if name in MUTATING_TOOLS and payload.get("confirm") is True:
                preview = await session.call_tool(name, payload | {"confirm": False})
                preview_data = preview.data
                assert isinstance(preview_data, dict)
                assert preview_data.get("status") == "confirmation_required"
                assert preview_data.get("api_called") is False
            result = await session.call_tool(name, payload)
            called_tools.add(name)
            data = result.data
            if isinstance(data, dict) and data.get("status") == "error":
                raise RuntimeError(f"{name}: {json.dumps(data['error'], sort_keys=True)}")
            return data

        try:
            status = await call("bundled_status")
            assert status["authenticated"] is True
            await call("bundled_current_user")
            checks.append("authenticated_read")

            preview = await call("bundled_create_bundle", {"spec": {"name": f"{prefix} MCP"}})
            assert preview["status"] == "confirmation_required" and preview["api_called"] is False
            checks.append("confirmation_gate")

            source = await call(
                "bundled_create_bundle",
                {"spec": {"name": f"{prefix} MCP", "description": "Disposable integration fixture"}, "confirm": True},
            )
            bundle_ids.append(source["id"])
            assert (await call("bundled_get_bundle", {"bundle_id": source["id"]}))["id"] == source["id"]
            source = await call(
                "bundled_update_bundle",
                {
                    "bundle_id": source["id"],
                    "spec": {"markdown_flavor": "gfm", "background": "tinted"},
                    "confirm": True,
                },
            )
            assert source["config"]["markdownFlavor"] == "gfm" and source["colourfulBackgrounds"] is True
            checks.append("bundle_crud")

            task = await call(
                "bundled_create_tag",
                {
                    "bundle_id": source["id"],
                    "spec": {"name": f"{prefix} Task", "task": True, "mark_complete": True},
                    "confirm": True,
                },
            )
            task = await call(
                "bundled_update_tag",
                {"bundle_id": source["id"], "tag_id": task["id"], "spec": {"color": "#4a4ddf"}, "confirm": True},
            )
            assert task["colorHex"] == "#4a4ddf"
            disposable_tag = await call(
                "bundled_create_tag",
                {"bundle_id": source["id"], "spec": {"name": f"{prefix} Delete me"}, "confirm": True},
            )
            await call(
                "bundled_delete_tag",
                {"bundle_id": source["id"], "tag_id": disposable_tag["id"], "confirm": True},
            )

            global_tag = await call(
                "bundled_create_tag",
                {"bundle_id": source["id"], "spec": {"name": f"{prefix} Global", "global_tag": True}, "confirm": True},
            )
            global_tags.append((source["id"], global_tag["id"]))
            checks.append("local_and_global_tags")

            entry = await call(
                "bundled_create_entry",
                {
                    "bundle_id": source["id"],
                    "spec": {"title": f"{prefix} Entry", "content": "# Live MCP\n\nunique integration text"},
                    "confirm": True,
                },
            )
            entry = await call(
                "bundled_update_entry",
                {
                    "bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "spec": {"title": f"{prefix} Updated", "pinned": True},
                    "confirm": True,
                },
            )
            assert entry["pinned"] is True
            listed_entries = await call("bundled_list_entries", {"bundle_id": source["id"]})
            assert any(item["id"] == entry["id"] for item in listed_entries["entries"])
            assert (await call("bundled_get_entry", {"bundle_id": source["id"], "entry_id": entry["id"]}))[
                "id"
            ] == entry["id"]
            listed_tags = await call("bundled_list_tags", {"bundle_id": source["id"]})
            assert any(item["id"] == task["id"] for item in listed_tags["tags"])
            entry = await call(
                "bundled_apply_tag",
                {
                    "bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "tag_id": task["id"],
                    "apply_actions": True,
                    "confirm": True,
                },
            )
            assert entry["markedAsComplete"] is True and task["id"] in entry["associatedTagIds"]
            entry = await call(
                "bundled_remove_tag",
                {
                    "bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "tag_id": task["id"],
                    "confirm": True,
                },
            )
            assert task["id"] not in entry["associatedTagIds"]
            entry = await call(
                "bundled_apply_tag",
                {
                    "bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "tag_id": task["id"],
                    "apply_actions": False,
                    "confirm": True,
                },
            )
            matches = await call(
                "bundled_search_entries", {"query": "unique integration text", "bundle_id": source["id"]}
            )
            assert matches["count"] == 1
            await call(
                "bundled_set_entry_state",
                {
                    "bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "state": "archived",
                    "value": True,
                    "confirm": True,
                },
            )
            entry = await call(
                "bundled_set_entry_state",
                {
                    "bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "state": "archived",
                    "value": False,
                    "confirm": True,
                },
            )
            assert entry["archived"] is False
            checks.append("entry_crud_search_task_archive")

            board = await call(
                "bundled_create_bundle",
                {"spec": {"name": f"{prefix} Board", "template": "list"}, "confirm": True},
            )
            bundle_ids.append(board["id"])
            column_tags = []
            for name, color in (("To Do", "#4a4ddf"), ("Doing", "#e9860c"), ("Done", "#0ce986")):
                column_tags.append(
                    await call(
                        "bundled_create_tag",
                        {
                            "bundle_id": board["id"],
                            "spec": {"name": f"{prefix} {name}", "color": color},
                            "confirm": True,
                        },
                    )
                )
            columns = [tag["id"] for tag in column_tags]
            await call(
                "bundled_configure_kanban",
                {"bundle_id": board["id"], "column_tag_ids": columns, "backlog_name": "Inbox", "confirm": True},
            )
            moved = await call(
                "bundled_move_entry",
                {
                    "source_bundle_id": source["id"],
                    "entry_id": entry["id"],
                    "target_bundle_id": board["id"],
                    "target_tag_ids": [columns[0]],
                    "confirm": True,
                },
            )
            moved = await call(
                "bundled_move_kanban_entry",
                {
                    "bundle_id": board["id"],
                    "entry_id": moved["id"],
                    "target_column_tag_id": columns[1],
                    "confirm": True,
                },
            )
            assert columns[1] in moved["associatedTagIds"] and columns[0] not in moved["associatedTagIds"]
            copied = await call(
                "bundled_duplicate_entry",
                {
                    "source_bundle_id": board["id"],
                    "entry_id": moved["id"],
                    "target_bundle_id": board["id"],
                    "target_tag_ids": [columns[2]],
                    "confirm": True,
                },
            )
            assert copied["id"] != moved["id"]
            await call(
                "bundled_delete_entry",
                {"bundle_id": board["id"], "entry_id": copied["id"], "confirm": True},
            )
            checks.append("move_copy_kanban")

            template = await call(
                "bundled_create_template",
                {"bundle_id": board["id"], "name": f"{prefix} Template", "include_entries": False, "confirm": True},
            )
            template_ids.append(template["id"])
            applied = await call(
                "bundled_apply_template",
                {"template_id": template["id"], "name": f"{prefix} Applied", "confirm": True},
            )
            bundle_ids.append(applied["id"])
            assert applied["name"] == f"{prefix} Applied"
            applied_tags = await call("bundled_list_tags", {"bundle_id": applied["id"], "include_global": False})
            assert applied_tags["count"] == 3
            assert all(tag["bundleId"] == applied["id"] for tag in applied_tags["tags"])
            checks.append("template_create_apply")

            payload = b"0123456789012345678901234567890123456789012345678"
            filename = f"mcp-test-{run_id}.txt"
            uploaded = await call(
                "bundled_upload_attachment",
                {
                    "bundle_id": board["id"],
                    "entry_id": moved["id"],
                    "filename": filename,
                    "content_base64": base64.b64encode(payload).decode("ascii"),
                    "confirm": True,
                },
            )
            attachment_id = uploaded["attachment"]["id"]
            account_attachment_ids.append(attachment_id)
            assert uploaded["attachment"]["text"] == filename
            assert uploaded["attachment"]["fileSize"] == len(payload)
            catalog = await call("bundled_list_attachments")
            catalog_item = next(item for item in catalog["attachments"] if item["id"] == attachment_id)
            assert catalog_item["text"] == filename and catalog_item["fileSize"] == len(payload)
            schema = await call("bundled_schema_status", {"sample_size": 25})
            assert schema["compatible"] is True, json.dumps(schema, sort_keys=True)
            checks.append("sanitized_schema_contract")
            detached = await call(
                "bundled_remove_attachment",
                {
                    "bundle_id": board["id"],
                    "entry_id": moved["id"],
                    "attachment_id": attachment_id,
                    "confirm": True,
                },
            )
            assert attachment_id not in detached.get("attachments", {})
            await call("bundled_delete_account_attachment", {"attachment_id": attachment_id, "confirm": True})
            account_attachment_ids.remove(attachment_id)
            checks.append("attachment_upload_detach_delete")

            await call(
                "bundled_set_bundle_archived",
                {"bundle_id": applied["id"], "archived": True, "confirm": True},
            )
            restored = await call(
                "bundled_set_bundle_archived",
                {"bundle_id": applied["id"], "archived": False, "confirm": True},
            )
            assert restored["archived"] is False
            checks.append("bundle_archive_restore")
        finally:
            for attachment_id in list(account_attachment_ids):
                try:
                    await call("bundled_delete_account_attachment", {"attachment_id": attachment_id, "confirm": True})
                except Exception:
                    pass
            for bundle_id, tag_id in list(global_tags):
                try:
                    await call(
                        "bundled_delete_tag",
                        {
                            "bundle_id": bundle_id,
                            "tag_id": tag_id,
                            "global_tag": True,
                            "allow_dangling_references": True,
                            "confirm": True,
                        },
                    )
                except Exception:
                    pass
            for template_id in reversed(template_ids):
                try:
                    await call("bundled_delete_template", {"template_id": template_id, "confirm": True})
                except Exception:
                    pass
            for bundle_id in reversed(bundle_ids):
                try:
                    await call("bundled_delete_bundle", {"bundle_id": bundle_id, "confirm": True})
                except Exception:
                    pass

        remaining_bundles = await call("bundled_list_bundles", {"include_archived": True, "limit": 1000})
        remaining_templates = await call("bundled_list_templates", {"limit": 1000})
        remaining_attachments = await call("bundled_list_attachments", {"limit": 1000})
        assert not any(run_id in item.get("name", "") for item in remaining_bundles["bundles"])
        assert not any(run_id in item.get("name", "") for item in remaining_templates["templates"])
        assert not any(run_id in item.get("text", "") for item in remaining_attachments["attachments"])
        checks.append("mcp_artifact_cleanup_verified")

        runtime_tools = {tool.name for tool in await session.list_tools()}
        missing_tools = sorted(runtime_tools - called_tools)
        assert not missing_tools, f"Live integration did not execute: {missing_tools}"
        checks.append("complete_tool_catalog_coverage")

    return {"ok": True, "run_id": run_id, "checks": checks, "tools_executed": len(called_tools)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    print(json.dumps(asyncio.run(run(parser.parse_args().run_id)), sort_keys=True))


if __name__ == "__main__":
    main()
