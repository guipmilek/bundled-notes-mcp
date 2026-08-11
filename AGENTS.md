# Bundled Notes MCP - Agent Instructions

## Project

Unofficial Python/FastMCP server for Bundled Notes Web. Source lives under
`src/bundled_notes_mcp/`; tests live under `tests/`. Supported runtimes are local
stdio and the authenticated Prefect Horizon deployment at
`https://bundled-notes-mcp.fastmcp.app/mcp`.

## Mandatory rules

1. Read `llms.txt` before non-trivial changes.
2. Keep every write/destructive tool gated by `confirm: true`.
3. Keep MCP behavior annotations explicit and accurate.
4. Never commit `.env`, credentials, refresh/ID tokens, sessions, API responses,
   private note contents, attachment files, or Firebase download tokens.
5. Never accept a Bundled Notes password as an MCP tool argument.
6. Preserve unknown Firestore fields with partial updates.
7. Re-read confirmed writes and keep compensating cleanup for multi-step mutations.
8. Update docs and `llms.txt` when architecture, commands, tools, or security change.
9. Use only uniquely prefixed disposable records for live integration tests and
   verify their removal afterward.
10. Keep Horizon authentication enabled and MCP request/response payload logging
    disabled; production data can contain private notes and attachment metadata.
11. Before adapting to a Bundled Notes release, run the sanitized schema audit and
    follow `docs/schema-maintenance.md`; never commit rollout/session exports.

## Ownership

- `server.py`: FastMCP instance and stdio entrypoint.
- `tools.py`: public tools, annotations, and confirmation gates.
- `client.py`: Bundled Notes domain operations and verification.
- `auth.py`: Firebase refresh/sign-in logic and in-memory token lock.
- `firestore.py`: Firestore REST codec and transport.
- `storage.py`: Firebase Storage upload/metadata/delete operations.
- `models.py`: schemas, enums, IDs, and color conversion.
- `schema.py`: privacy-safe schema observation, compatibility contract, and drift classification.
- `overrides.py`: hosted-client compatibility overrides layered on the base tool catalog.
- `tests/`: catalog, safety, codec, auth, and behavior checks.

## Verification

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp
uv build
```

Do not run authenticated integration scripts against pre-existing IDs. Never stage
`.env`, test attachments, or private account data.
