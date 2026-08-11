from __future__ import annotations

from fastmcp import FastMCP

from bundled_notes_mcp import __version__
from bundled_notes_mcp.overrides import register_tool_overrides
from bundled_notes_mcp.tools import register_tools

mcp = FastMCP(
    name="bundled-notes-mcp",
    version=__version__,
    mask_error_details=True,
    strict_input_validation=True,
    instructions=(
        "Unofficial Bundled Notes Web integration. Reads are direct. Every write requires confirm=true after "
        "reviewing IDs and payloads. Archive is reversible; delete tools are permanent. Never reveal refresh, ID, "
        "purchase, or Firebase download tokens."
    ),
)
register_tools(mcp)
register_tool_overrides(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
