# Agent Architecture Map

## Runtime flow

```text
Horizon OAuth / local stdio
  -> FastMCP server.py
  -> validated tool in tools.py
  -> BundledNotesClient in client.py
  -> Firebase Auth + Firestore / callable functions / Storage
```

Horizon owns hosted transport and inbound OAuth. This repository owns the FastMCP
object, Bundled Notes authentication, compatibility adapters, and all data-safety
rules. One configured process operates on one Bundled Notes account.

## Source ownership

- `server.py`: server metadata, registration, and stdio entrypoint.
- `tools.py`: public names, input/output schemas, annotations, and confirmation gates.
- `client.py`: domain operations, post-write verification, and compensating cleanup.
- `auth.py`: refresh/sign-in flow and in-memory token lock.
- `firestore.py`: Firestore REST codec and transport.
- `storage.py`: upload, metadata, bounded download, and deletion.
- `models.py`: enums, identifiers, schemas, and color conversion.
- `schema.py`: sanitized observation, contract, fingerprint, and drift classification.
- `overrides.py`: hosted-client compatibility wrappers over the base catalog.

## Change checklists

Tool change:

1. Update `tools.py` and the matching `BundledNotesClient` operation.
2. Preserve `confirm: true` for every write and accurate MCP annotations.
3. Add catalog, confirmation, persistence, and negative tests.
4. Synchronize both READMEs, `llms.txt`, `WRITES.md`, and relevant docs.

Upstream/schema change:

1. Run `bundled_schema_status` or `scripts/schema_audit.py` before writes.
2. Follow `schema-maintenance.md` and change the smallest compatibility seam.
3. Preserve unknown fields and legacy shapes that the app can still retain.
4. Run the disposable live audit and prove zero residue.

Deploy change:

1. Preserve `src/bundled_notes_mcp/server.py:mcp`.
2. Keep Horizon authentication enabled and payload logging disabled.
3. Update `deployment.md` and verify the catalog after deployment.
