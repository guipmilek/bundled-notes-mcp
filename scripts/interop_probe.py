from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from fastmcp import Client

from bundled_notes_mcp.server import mcp


async def call(session: Client[Any], name: str, arguments: dict[str, Any]) -> Any:
    result = await session.call_tool(name, arguments)
    data = result.data
    if isinstance(data, dict) and data.get("status") == "error":
        raise RuntimeError(json.dumps(data["error"], sort_keys=True))
    return data


async def main_async(args: argparse.Namespace) -> dict[str, Any]:
    async with Client(mcp) as session:
        if args.action == "create":
            name = f"[MCP TEST {args.run_id}] Interop"
            bundle = await call(
                session,
                "bundled_create_bundle",
                {"spec": {"name": name, "description": "MCP to web interoperability probe"}, "confirm": True},
            )
            try:
                entry = await call(
                    session,
                    "bundled_create_entry",
                    {
                        "bundle_id": bundle["id"],
                        "spec": {"title": name, "content": "Created through the MCP protocol; verified in the web UI."},
                        "confirm": True,
                    },
                )
            except Exception:
                await call(session, "bundled_delete_bundle", {"bundle_id": bundle["id"], "confirm": True})
                raise
            return {"bundle_id": bundle["id"], "entry_id": entry["id"], "name": name}
        if args.action == "read":
            entry = await call(
                session,
                "bundled_get_entry",
                {"bundle_id": args.bundle_id, "entry_id": args.entry_id},
            )
            return {"entry_id": entry["id"], "title": entry["title"], "last_edited_time": entry["lastEditedTime"]}
        return await call(session, "bundled_delete_bundle", {"bundle_id": args.bundle_id, "confirm": True})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "read", "cleanup"])
    parser.add_argument("--run-id")
    parser.add_argument("--bundle-id")
    parser.add_argument("--entry-id")
    args = parser.parse_args()
    if args.action == "create" and not args.run_id:
        parser.error("create requires --run-id")
    if args.action == "cleanup" and not args.bundle_id:
        parser.error("cleanup requires --bundle-id")
    if args.action == "read" and (not args.bundle_id or not args.entry_id):
        parser.error("read requires --bundle-id and --entry-id")
    print(json.dumps(asyncio.run(main_async(args)), sort_keys=True))


if __name__ == "__main__":
    main()
