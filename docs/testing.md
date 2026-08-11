# Testing

Unit tests cover Firestore value codecs, enum/color and schema validation, confirmation gates, error sanitization, token refresh behavior, and client write semantics with an in-memory Firestore double.

The authenticated integration protocol uses only uniquely prefixed artifacts:

1. Confirm a real authenticated account read.
2. Create an isolated bundle, tag/task, entry, board/template, and attachment.
3. Read every write back through Firestore and through the web UI where practical.
4. Exercise update, completion, pin, archive/restore, search, copy/move, Kanban, template apply, attach/detach/delete.
5. Recursively delete test templates and bundles, remove storage/catalog objects, and verify the prefix no longer occurs.

Never point an integration run at pre-existing IDs. Do not infer successful authentication from configuration alone. Avoid retries around creates, moves, uploads, and deletes.
