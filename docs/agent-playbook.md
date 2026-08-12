# Bundled Notes MCP Agent Playbook

## Preflight

1. Confirm the repository, branch, and working-tree scope.
2. Read `AGENTS.md`, `llms.txt`, this playbook, and the relevant domain document.
3. Classify the change: MCP contract, client behavior, Firebase codec/storage,
   authentication, schema compatibility, deployment, tests, or docs.
4. Run a sanitized schema check before adapting to an upstream release.
5. State the verification commands and whether a live test is required.

## Security invariants

- Every state-changing tool returns before the upstream API unless `confirm is True`.
- Tokens, credentials, private note content, filenames, signed URLs, and raw API
  responses never enter commits, fixtures, reports, or logs.
- Existing Firestore documents are partially patched so unknown fields survive.
- Confirmed writes are re-read; multi-step operations retain compensating cleanup.
- Authenticated tests use only `[MCP TEST <RUN_ID>]` records and remove all objects.
- Horizon remains authenticated and MCP request/response payload logging stays off.

## Verification ladder

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run fastmcp inspect src/bundled_notes_mcp/server.py:mcp
uv build
```

Run `scripts/schema_audit.py` for upstream drift. Run
`scripts/live_integration.py` only with explicit authorization and configured test
credentials; record only sanitized counts, field names/types, and test-owned IDs.

## Upstream work

1. Compare the Bundled Notes changelog, web behavior, and sanitized schema output.
2. Do not infer write contracts from a Firestore field alone.
3. Add old/new fixtures before changing adapters.
4. Keep MCP names and output shapes stable when feasible.
5. If an official API/MCP appears, place it behind `BundledNotesClient` and prove
   parity and rollback before retiring Firebase access.

## Handoff

Report changed files, checks and results, live checks skipped or completed,
schema fingerprint/status, remaining risks, and cleanup proof. Publish only through
the approved GitHub workflow and never merge without the repository owner's approval.
