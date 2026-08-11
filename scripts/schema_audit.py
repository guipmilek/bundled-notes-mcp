from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from fastmcp import Client

from bundled_notes_mcp.server import mcp


async def run(sample_size: int) -> dict[str, Any]:
    async with Client(mcp, timeout=60) as session:
        result = await session.call_tool("bundled_schema_status", {"sample_size": sample_size})
        data = result.data
        if not isinstance(data, dict):
            raise RuntimeError("bundled_schema_status returned an unexpected response.")
        if data.get("status") == "error":
            raise RuntimeError(json.dumps(data["error"], sort_keys=True))
        return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare sanitized Bundled Notes field shapes with the supported MCP schema contract."
    )
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Optional JSON report path; contains field names/types only.")
    parser.add_argument(
        "--fail-on",
        choices=["breaking", "additive", "never"],
        default="breaking",
        help="Exit non-zero for breaking drift (default), any drift, or never.",
    )
    args = parser.parse_args()
    report = asyncio.run(run(args.sample_size))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")

    should_fail = (args.fail_on == "breaking" and not report["compatible"]) or (
        args.fail_on == "additive" and report["status"] != "compatible"
    )
    if should_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
