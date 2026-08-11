# Testing

Unit tests cover Firestore value codecs, enum/color and schema validation, confirmation gates, error sanitization, token refresh behavior, the Firebase multipart upload wire format, exact attachment metadata, compensating cleanup, and client write semantics with an in-memory Firestore double.

`scripts/schema_audit.py` is read-only and emits only field names and value types.
It distinguishes compatible, additive, and breaking drift and exits non-zero for
breaking changes. The scheduled GitHub workflow uses the same probe when its
repository secrets are configured.

The authenticated integration protocol uses only uniquely prefixed artifacts:

1. Confirm a real authenticated account read.
2. Create an isolated bundle, tag/task, entry, board/template, and attachment.
3. Read every write back through Firestore and through the web UI where practical; compare attachment filename and byte size between upload, account catalog, and entry reference.
4. Exercise update, completion, pin, archive/restore, search, copy/move, Kanban, template apply, attach/detach/delete.
5. Recursively delete test templates and bundles, remove storage/catalog objects, and verify the prefix no longer occurs.
6. Confirm every runtime tool was executed and the live sanitized schema remains compatible.

Live Kanban fixtures start as a list and use explicitly prefixed column tags, so
every generated record follows the exact `RUN_ID`. Template application must also
rebind every copied local tag's `bundleId` to the destination bundle.

Never point an integration run at pre-existing IDs. Do not infer successful authentication from configuration alone. Avoid retries around creates, moves, uploads, and deletes.
