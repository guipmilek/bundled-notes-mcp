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
- Authenticated downloads return Base64 only up to 10 MiB and never expose signed
  Firebase Storage URLs or tokens.
- Entry moves create and verify the destination before deleting the source, with
  compensating cleanup if source deletion fails.
- Tag deletion refuses dangling entry/Kanban references by default.
- Uploads respect the observed 400 MiB file limit, verify Storage size/metadata,
  re-read the catalog, and compensate partial failures.
- `bundled_schema_status` compares sanitized Firestore shapes with a versioned
  contract without returning titles, content, filenames, IDs, or other values.

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

### Prefect Horizon (hosted)

The official deployment for this repository is available at:

```text
https://bundled-notes-mcp.fastmcp.app/mcp
```

The endpoint requires Horizon authentication and automatically promotes
successful builds from `main`. In Horizon, use
`src/bundled_notes_mcp/server.py:mcp` as the entrypoint, `pyproject.toml` as the
requirements file, and configure the Firebase variables as secrets. Keep MCP
request and response payload logging disabled because it may contain private
notes and metadata.

### Local (stdio)

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
| Compatibility | Sanitized schema audit and additive/breaking drift detection |
| Backup | Export an account or one bundle as structured JSON |
| Bundles | List, get, create, update, reorder, archive, restore, and delete |
| Entries | List, search, create, update, reorder, duplicate, move, complete, and delete |
| Tags/tasks | Manage local/global tags, subscriptions, priority, and actions |
| Kanban | Configure ordered tag columns and move entries to a column/backlog |
| Templates | Create from bundle, apply, and delete |
| Files & Photos | List, download up to 10 MiB, upload, attach, detach, and delete |
| Rich links | Generate or refresh previews through the native callable function |
| Reminders | List reminder metadata attached to entries |

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
[data model](docs/data-model.md), [schema maintenance](docs/schema-maintenance.md),
and [testing](docs/testing.md).

## Known limits

- Firebase endpoints and Firestore paths are implementation details, not a
  compatibility promise.
- Reminder writes remain blocked until the Android scheduling/notification
  contract can be validated end-to-end; a Firestore write alone is not treated as
  functional reminder support.
- Google Keep import remains out of scope while the official flow is still under development.
- Detach account files from relevant entries before deleting them.
- User-document counters may lag; collection-listing tools are authoritative for
  this server.
