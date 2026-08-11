# Firebase data model

All paths are scoped below `users/{uid}`:

```text
users/{uid}
├── bundles/{bundleId}
│   ├── entries/{entryId}
│   └── tags/{tagId}
├── tags/{globalTagId}
├── templates/{templateId}
│   ├── entries/{entryId}
│   └── tags/{tagId}
└── attachments/{attachmentId}
```

Storage objects use `users/{uid}/{storageId}`. Firestore documents normally duplicate their document ID in an `id` field.

## Core fields

- Bundle: `id`, `ownerId`, `name`, `description`, layout/sort/display fields, `config`, archive/default/Kanban fields, and global-tag subscriptions.
- Entry: `id`, `numericId`, `parentBundleId`, `title`, `content`, `associatedTagIds`, timestamps, type, state booleans, device name, index, and attachment map.
- Tag: `id`, `bundleId`, name/color/index/default fields and task action fields.
- Attachment: `id`, `uid`, `storageId`, `type`, `fileSize`, and display text/filename.

Firestore REST integers are encoded as strings on the wire and decoded to Python integers. Color values are signed 32-bit integers; the MCP accepts `#RRGGBB` or `#AARRGGBB` and returns a convenience `colorHex` alongside the raw value.

## Exact enum observations

Entry sort: alphabetical `0`, reverse alphabetical `1`, updated oldest `2`, updated newest `3`, managed `4`, created oldest `5`, created newest `6`.

Web layouts: compact `0`, grid `1`, standard/card `2`. Markdown flavors: `legacy`, `gfm`. Entry types: solo `-17`, mixed `-12`, solo image `-23`.

Attachment types: rich link `1`, file from device/account `5/6`, image from account/device `17/18`, image URL `32`, arbitrary text `99`, reminder text `102`.

Template tag snapshots can retain the source bundle ID while stored below
`templates/{templateId}/tags`. When a template is applied, copied local tags are
rebound to the newly created bundle through `bundleId`.
