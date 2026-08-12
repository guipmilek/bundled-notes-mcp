# Project Paths

## Repository

| Purpose | Path |
| --- | --- |
| Python package | `src/bundled_notes_mcp/` |
| Tests | `tests/` |
| Operational scripts | `scripts/` |
| Maintainer documentation | `docs/` |
| MCP entrypoint | `src/bundled_notes_mcp/server.py:mcp` |
| Tool catalog | `src/bundled_notes_mcp/tools.py` |
| Schema contract | `src/bundled_notes_mcp/schema.py` |

All paths are repository-relative so forks and local checkouts remain portable.

## Runtime

- Python `>=3.11`
- uv for dependency and command execution
- FastMCP 3
- Prefect Horizon for one user-owned fork/deployment per account
- Firebase Auth, Firestore REST, callable functions, and Firebase Storage behind
  `BundledNotesClient`

`.venv/`, `.env`, private attachments, session exports, generated schema reports,
logs, coverage, and agent checkpoints must remain untracked. Verify any copied
external path before accessing it.
