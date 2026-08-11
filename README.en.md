<p align="right">
  <img src="https://img.shields.io/badge/lang-en-green?style=flat-square&amp;labelColor=202024" alt="English" />
  <a href="./README.md"><img src="https://img.shields.io/badge/lang-pt--br-gray?style=flat-square&amp;labelColor=202024" alt="Português" /></a>
</p>

<h1 id="top" align="center">Bundled Notes MCP</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-%3E%3D3.11-3776ab?style=flat-square&amp;logo=python&amp;logoColor=white&amp;labelColor=202024" alt="Python >= 3.11" />
  <img src="https://img.shields.io/badge/FastMCP-3.x-7c3aed?style=flat-square&amp;labelColor=202024" alt="FastMCP 3" />
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square&amp;labelColor=202024" alt="MIT" /></a>
</p>

<p align="center">Unofficial MCP server for reading and managing an authenticated Bundled Notes Web account.</p>

This local-first server exposes bundles, Markdown entries, tags/tasks, Kanban
boards, custom templates, search, and Files & Photos through the same Firebase
data model used by the web app.

> [!WARNING]
> This project is not affiliated with Bundled Notes. The web app does not publish
> a stable or supported API; upstream schema or Firebase-rule changes can break
> the integration. Keep a backup and inspect every proposed write.

## Safety contract

- Every state-changing tool returns `confirmation_required` without an API call
  unless `confirm=true`.
- Archive/restore operations are explicit. Permanent delete tools are clearly
  named and recursively remove known Firestore subcollections when required.
- Updates use Firestore update masks so unknown upstream fields are preserved.
- Authentication, purchase, and download tokens are never returned by MCP tools.
- Entry moves create and verify the destination before deleting the source, with
  compensating cleanup if source deletion fails.
- Tag deletion refuses dangling entry/Kanban references by default.
- Uploads respect the observed 400 MiB file limit and compensate partial failures.

Read [WRITES.md](WRITES.md) before enabling mutations.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run bundled-notes-bootstrap-auth --output .env
uv run bundled-notes-mcp
```

The bootstrap command interactively requests the Bundled Notes credentials,
discovers the current public Firebase configuration, and writes a gitignored
`.env` without printing the password or refresh token. If discovery stops
working, pass the current public key with `--api-key`.

Example Codex configuration:

```toml
[mcp_servers.bundled-notes]
command = "uv"
args = ["--directory", "C:/path/to/bundled-notes-mcp", "run", "bundled-notes-mcp"]
```

Start with `bundled_status` and `bundled_list_bundles`. For a write, call once
without confirmation, inspect the IDs and payload, and repeat with `confirm=true`.

## Tool groups

| Group | Capabilities |
| --- | --- |
| Account | Authenticated status and safe user projection |
| Bundles | List, get, create, update, archive, restore, and delete |
| Entries | List, search, create, update, duplicate, move, complete, and delete |
| Tags/tasks | Create, update, apply, remove, swap, and execute actions |
| Kanban | Configure ordered tag columns and move entries to a column/backlog |
| Templates | Create from bundle, apply, and delete |
| Files & Photos | List, upload, attach, detach, and delete |

Search filters downloaded entries client-side because the web app also relies on
a local cache/index instead of a Firestore full-text endpoint.

## Development

```powershell
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp
uv build
```

See [reverse engineering](docs/reverse-engineering.md),
[data model](docs/data-model.md), and [testing](docs/testing.md).

## Known limits

- Firebase endpoints and Firestore paths are implementation details, not a
  compatibility promise.
- Google Keep import, JSON export, reminders, and derived rich-link-preview
  generation are observed but are not mutation tools in `0.1.0`.
- Detach account files from relevant entries before deleting them.
- User-document counters may lag; collection-listing tools are authoritative for
  this server.
