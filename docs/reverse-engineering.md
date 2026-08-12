# Reverse-engineering notes

Validated against the authenticated Bundled Notes Web application on 2026-08-11. The inspection combined visible UI workflows, network behavior, static production JavaScript, Firestore read-backs, and isolated create/update/delete probes. All probes used a unique `[MCP TEST ...]` prefix and were removed afterward.

## Surface inventory

The web client supports email/Google login, global local-cache search, Files & Photos, themes and typography, rich-link previews, Markdown flavor selection, Google Keep import, changelog/help, bundles, entries, tags/tasks, Kanban boards, and custom templates.

Bundle templates are Notes (grid plus a default General tag), List (standard layout), and Board (standard layout with To Do, Doing, and Done tag columns). Bundle settings cover names, description, item nouns, default bundle, layouts, sorting/grouping, tag priority, background tinting, preview density, timestamps, completion ordering, reminders, and board/backlog behavior.

Entry editing supports Markdown title/content, tags, pin, archive/restore, completion, attachments, delete, duplicate, and cross-bundle move/copy. A move creates a new destination document ID, then removes the source. Kanban movement replaces the old column tag with the destination column tag while preserving unrelated tags.

The web client invokes `buildRichPreviewsForEntry` with `uid`, `bundleId`,
`entryId`, and optional `refreshAttachmentId`. It orders bundles/entries with
`indexPosition`, tags with `tagPriorityOrder`, and stores visible account-global
tags in each bundle's `subscribedGlobalTagIds`.

Tags can be bundle-local or global/subscribed. A task tag can mark complete, archive, and swap tags. The current client stores task action mode `4` with explicit booleans for those actions.

Custom templates copy a bundle's configuration and tags, optionally entries, then instantiate a new bundle. Files & Photos stores an account catalog document plus an object under the user's Firebase Storage prefix; an entry holds a metadata map keyed by the attachment ID.

## Compatibility posture

There is no public, versioned Bundled Notes API contract. This MCP therefore:

- confines paths and enum mappings to small modules;
- uses partial update masks;
- preserves unknown fields when copying records;
- verifies writes by re-reading the affected document;
- fails with sanitized errors when Firebase rules reject an operation;
- never retries non-idempotent creates automatically.
- observes field names/types through a privacy-safe versioned schema contract;
- treats new fields as additive drift and missing/type-changed required fields as breaking drift.

Observed enum mappings and defaults are in `src/bundled_notes_mcp/models.py` and `BundledNotesClient._bundle_defaults`.
The repeatable update procedure is in `docs/schema-maintenance.md`.
