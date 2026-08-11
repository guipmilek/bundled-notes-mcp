from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from fastmcp import Client

from bundled_notes_mcp.server import mcp


async def run(run_id: str) -> dict[str, Any]:
    marker = f"[MCP TEST {run_id}"
    removed: dict[str, list[str]] = {"attachments": [], "templates": [], "bundles": []}
    async with Client(mcp, timeout=60) as session:

        async def call(name: str, arguments: dict[str, Any] | None = None) -> Any:
            result = await session.call_tool(name, arguments or {})
            data = result.data
            if isinstance(data, dict) and data.get("status") == "error":
                raise RuntimeError(json.dumps(data["error"], sort_keys=True))
            return data

        attachments = (await call("bundled_list_attachments", {"limit": 1000}))["attachments"]
        for attachment in attachments:
            if run_id in str(attachment.get("text", "")):
                await call(
                    "bundled_delete_account_attachment",
                    {"attachment_id": attachment["id"], "confirm": True},
                )
                removed["attachments"].append(attachment["id"])

        templates = (await call("bundled_list_templates", {"limit": 1000}))["templates"]
        for template in templates:
            if str(template.get("name", "")).startswith(marker):
                await call("bundled_delete_template", {"template_id": template["id"], "confirm": True})
                removed["templates"].append(template["id"])

        bundles = (await call("bundled_list_bundles", {"include_archived": True, "limit": 1000}))["bundles"]
        for bundle in bundles:
            if str(bundle.get("name", "")).startswith(marker):
                await call("bundled_delete_bundle", {"bundle_id": bundle["id"], "confirm": True})
                removed["bundles"].append(bundle["id"])

        remaining_bundles = (await call("bundled_list_bundles", {"include_archived": True, "limit": 1000}))["bundles"]
        remaining_templates = (await call("bundled_list_templates", {"limit": 1000}))["templates"]
        remaining_attachments = (await call("bundled_list_attachments", {"limit": 1000}))["attachments"]
        residue = {
            "bundles": [item["id"] for item in remaining_bundles if marker in str(item.get("name", ""))],
            "templates": [item["id"] for item in remaining_templates if marker in str(item.get("name", ""))],
            "attachments": [item["id"] for item in remaining_attachments if run_id in str(item.get("text", ""))],
        }
        if any(residue.values()):
            raise RuntimeError(f"Cleanup residue: {json.dumps(residue, sort_keys=True)}")
        return {"ok": True, "removed": removed, "remaining_bundle_count": len(remaining_bundles)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove only Bundled Notes MCP test artifacts for an exact run ID.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--confirm", required=True, choices=["DELETE-MCP-TEST-ARTIFACTS"])
    print(json.dumps(asyncio.run(run(parser.parse_args().run_id)), sort_keys=True))


if __name__ == "__main__":
    main()
