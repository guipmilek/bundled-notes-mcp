from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from .auth import FirebaseAuth
from .errors import BundledNotesError
from .firestore import Firestore
from .models import (
    ATTACHMENT_TYPES,
    ENTRY_TYPES,
    LAYOUTS,
    SORT_METHODS,
    BundleCreate,
    BundleUpdate,
    EntryCreate,
    EntryUpdate,
    TagCreate,
    TagUpdate,
    compact_document,
    hex_to_signed_color,
    new_id,
    new_numeric_id,
)
from .storage import FirebaseStorage


class BundledNotesClient:
    def __init__(self, auth: FirebaseAuth) -> None:
        self.auth = auth
        self.db = Firestore(auth)
        self.storage = FirebaseStorage(auth)

    async def uid(self) -> str:
        return (await self.auth.token()).uid

    async def user_path(self) -> str:
        return f"users/{await self.uid()}"

    async def current_user(self) -> dict[str, Any]:
        raw = await self.db.get(await self.user_path()) or {}
        allowed = {
            "id",
            "proSubscriber",
            "subscriptionExpiryTime",
            "subscriptionSku",
            "subscriptionMethod",
            "accountOnHold",
            "storageUsedInBytes",
            "storageLeftInBytes",
            "numberOfBundles",
            "numberOfArchivedBundles",
            "defaultBundle",
            "settings",
            "acceptedPrivacyPolicyVersion",
            "seenChangelogVersion",
        }
        result = {key: value for key, value in raw.items() if key in allowed}
        if isinstance(result.get("settings"), dict):
            safe_settings = {"seenWebAppChangeLogVersion", "automaticallyFetchLinkPreviews"}
            result["settings"] = {key: value for key, value in result["settings"].items() if key in safe_settings}
        result["uid"] = await self.uid()
        return result

    async def list_bundles(self, *, include_archived: bool = False, limit: int = 300) -> list[dict[str, Any]]:
        rows = await self.db.list(f"{await self.user_path()}/bundles", page_size=limit)
        values = [compact_document(row) for row in rows if include_archived or not row.get("archived", False)]
        return sorted(values, key=lambda row: (row.get("indexPosition", 0), str(row.get("name", "")).lower()))

    async def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        return compact_document(await self._require(f"{await self.user_path()}/bundles/{bundle_id}"))

    async def create_bundle(self, spec: BundleCreate) -> dict[str, Any]:
        uid, bundle_id = await self.uid(), new_id()
        fields = self._bundle_defaults(uid, bundle_id, spec)
        bundle_path = f"users/{uid}/bundles"
        await self.db.create(bundle_path, bundle_id, fields)
        if spec.template == "notes":
            await self.create_tag(bundle_id, TagCreate(name="General", color="#e9860c", default_tag=True))
        elif spec.template == "board":
            tag_specs = [
                TagCreate(name="To Do", color="#4a4ddf"),
                TagCreate(name="Doing", color="#e9860c"),
                TagCreate(name="Done", color="#0ce986"),
            ]
            tags = [await self.create_tag(bundle_id, item) for item in tag_specs]
            await self.db.patch(f"{bundle_path}/{bundle_id}", {"kanbanColumnIds": [row["id"] for row in tags]})
        if spec.default_bundle:
            await self.db.patch(f"users/{uid}", {"defaultBundle": bundle_id})
        return await self.get_bundle(bundle_id)

    async def update_bundle(self, bundle_id: str, spec: BundleUpdate) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        direct = {
            "name": spec.name,
            "description": spec.description,
            "contentNameSingle": spec.content_name_single,
            "contentNamePlural": spec.content_name_plural,
            "compactTags": spec.compact_tags,
            "numberedList": spec.numbered_list,
            "showCreationDate": spec.show_creation_date,
            "showLastEditedTime": spec.show_last_edited_time,
            "hideFirstTag": spec.hide_first_tag,
            "numberOfLinesForPreview": spec.preview_lines,
            "numberOfAttachmentsForPreview": spec.preview_attachments,
            "keepCompleteItemsAtBottom": spec.keep_complete_at_bottom,
            "groupTagsTogether": spec.group_tags_together,
            "orderByRemindersFirst": spec.order_reminders_first,
        }
        fields.update({key: value for key, value in direct.items() if value is not None})
        if spec.layout is not None:
            fields["entriesLayoutTypeWeb"] = LAYOUTS[spec.layout]
        if spec.sort_method is not None:
            fields["bundleEntrySortMethod"] = SORT_METHODS[spec.sort_method]
        if spec.background is not None:
            fields["colourfulBackgrounds"] = spec.background != "none"
            fields["richColourfulBackgrounds"] = spec.background == "rich"
        if spec.markdown_flavor is not None:
            current = await self.get_bundle(bundle_id)
            config = dict(current.get("config") or {})
            config["markdownFlavor"] = spec.markdown_flavor
            fields["config"] = config
        path = f"{await self.user_path()}/bundles/{bundle_id}"
        await self.db.patch(path, fields)
        if spec.default_bundle is True:
            await self.db.patch(await self.user_path(), {"defaultBundle": bundle_id})
        elif spec.default_bundle is False:
            user = await self.current_user()
            if user.get("defaultBundle") == bundle_id:
                await self.db.patch(await self.user_path(), {"defaultBundle": ""})
        return await self.get_bundle(bundle_id)

    async def set_bundle_archived(self, bundle_id: str, archived: bool) -> dict[str, Any]:
        path = f"{await self.user_path()}/bundles/{bundle_id}"
        await self.db.patch(path, {"archived": archived})
        return await self.get_bundle(bundle_id)

    async def delete_bundle(self, bundle_id: str) -> dict[str, Any]:
        uid = await self.uid()
        base = f"users/{uid}/bundles/{bundle_id}"
        bundle = await self._require(base)
        entries, tags = await asyncio.gather(self.db.list(f"{base}/entries"), self.db.list(f"{base}/tags"))
        for row in entries:
            await self.db.delete(f"{base}/entries/{row['id']}")
        for row in tags:
            await self.db.delete(f"{base}/tags/{row['id']}")
        await self.db.delete(base)
        return {
            "deleted": True,
            "bundle_id": bundle_id,
            "name": bundle.get("name"),
            "deleted_entries": len(entries),
            "deleted_tags": len(tags),
        }

    async def list_entries(
        self, bundle_id: str, *, include_archived: bool = False, limit: int = 300
    ) -> list[dict[str, Any]]:
        rows = await self.db.list(f"{await self.user_path()}/bundles/{bundle_id}/entries", page_size=limit)
        return [compact_document(row) for row in rows if include_archived or not row.get("archived", False)]

    async def get_entry(self, bundle_id: str, entry_id: str) -> dict[str, Any]:
        return compact_document(await self._require(f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"))

    async def create_entry(self, bundle_id: str, spec: EntryCreate) -> dict[str, Any]:
        uid, entry_id, now = await self.uid(), new_id(), int(time.time() * 1000)
        fields = {
            "id": entry_id,
            "parentBundleId": bundle_id,
            "title": spec.title,
            "content": spec.content,
            "associatedTagIds": list(dict.fromkeys(spec.tag_ids)),
            "pinned": spec.pinned,
            "archived": spec.archived,
            "markedAsComplete": spec.completed,
            "attachments": {},
            "createdTime": now,
            "lastEditedTime": now,
            "indexPosition": 0,
            "numericId": new_numeric_id(),
            "type": ENTRY_TYPES["mixed"],
            "deviceName": "bundled-notes-mcp",
        }
        await self.db.create(f"users/{uid}/bundles/{bundle_id}/entries", entry_id, fields)
        return await self.get_entry(bundle_id, entry_id)

    async def update_entry(self, bundle_id: str, entry_id: str, spec: EntryUpdate) -> dict[str, Any]:
        fields: dict[str, Any] = {"lastEditedTime": int(time.time() * 1000), "deviceName": "bundled-notes-mcp"}
        if spec.title is not None:
            fields["title"] = spec.title
        if spec.content is not None:
            fields["content"] = spec.content
        if spec.tag_ids is not None:
            fields["associatedTagIds"] = list(dict.fromkeys(spec.tag_ids))
        if spec.pinned is not None:
            fields["pinned"] = spec.pinned
        path = f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"
        await self.db.patch(path, fields)
        return await self.get_entry(bundle_id, entry_id)

    async def set_entry_state(self, bundle_id: str, entry_id: str, field: str, value: bool) -> dict[str, Any]:
        allowed = {"archived", "markedAsComplete", "pinned"}
        if field not in allowed:
            raise BundledNotesError("invalid_state_field", "Unsupported entry state field.")
        path = f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"
        await self.db.patch(path, {field: value})
        return await self.get_entry(bundle_id, entry_id)

    async def delete_entry(self, bundle_id: str, entry_id: str) -> dict[str, Any]:
        path = f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"
        entry = await self._require(path)
        await self.db.delete(path)
        return {"deleted": True, "bundle_id": bundle_id, "entry_id": entry_id, "title": entry.get("title")}

    async def duplicate_entry(
        self, source_bundle_id: str, entry_id: str, target_bundle_id: str, target_tag_ids: list[str] | None = None
    ) -> dict[str, Any]:
        source = await self.get_entry(source_bundle_id, entry_id)
        return await self._copy_entry(source, target_bundle_id, target_tag_ids)

    async def move_entry(
        self, source_bundle_id: str, entry_id: str, target_bundle_id: str, target_tag_ids: list[str] | None = None
    ) -> dict[str, Any]:
        source = await self.get_entry(source_bundle_id, entry_id)
        created = await self._copy_entry(source, target_bundle_id, target_tag_ids)
        try:
            await self.db.delete(f"{await self.user_path()}/bundles/{source_bundle_id}/entries/{entry_id}")
        except Exception:
            await self.db.delete(f"{await self.user_path()}/bundles/{target_bundle_id}/entries/{created['id']}")
            raise
        return created

    async def search(
        self,
        query: str,
        *,
        bundle_id: str | None = None,
        tag_id: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        needle = query.casefold().strip()
        bundles = [await self.get_bundle(bundle_id)] if bundle_id else await self.list_bundles(include_archived=True)
        matches: list[dict[str, Any]] = []
        for bundle in bundles:
            if bundle.get("archived") and not include_archived:
                continue
            entries = await self.list_entries(bundle["id"], include_archived=include_archived, limit=1000)
            for entry in entries:
                if tag_id and tag_id not in (entry.get("associatedTagIds") or []):
                    continue
                haystack = f"{entry.get('title', '')}\n{entry.get('content', '')}".casefold()
                if needle in haystack:
                    matches.append({"bundle": {"id": bundle["id"], "name": bundle.get("name")}, "entry": entry})
                    if len(matches) >= limit:
                        return matches
        return matches

    async def list_tags(self, bundle_id: str, *, include_global: bool = True) -> list[dict[str, Any]]:
        uid = await self.uid()
        bundle_tags = await self.db.list(f"users/{uid}/bundles/{bundle_id}/tags")
        values = [compact_document(row) | {"scope": "bundle"} for row in bundle_tags]
        if include_global:
            bundle = await self.get_bundle(bundle_id)
            subscribed = set(bundle.get("subscribedGlobalTagIds") or [])
            if subscribed:
                globals_ = await self.db.list(f"users/{uid}/tags")
                values.extend(
                    compact_document(row) | {"scope": "global"} for row in globals_ if row.get("id") in subscribed
                )
        return sorted(values, key=lambda row: (row.get("indexPosition", 10_000_000), str(row.get("name", "")).lower()))

    async def create_tag(self, bundle_id: str, spec: TagCreate) -> dict[str, Any]:
        uid, tag_id = await self.uid(), new_id()
        fields = {
            "id": tag_id,
            "bundleId": bundle_id,
            "name": spec.name,
            "color": hex_to_signed_color(spec.color),
            "indexPosition": 10_000_000,
            "todoable": bool(spec.task or spec.mark_complete or spec.archive_note or spec.swap_tag_ids),
            "markedCompleteAction": 4,
            "swapTagIds": list(dict.fromkeys(spec.swap_tag_ids)),
            "markNoteAsComplete": spec.mark_complete,
            "archiveNote": spec.archive_note,
            "swapTags": bool(spec.swap_tag_ids),
            "defaultTag": spec.default_tag,
        }
        collection = f"users/{uid}/tags" if spec.global_tag else f"users/{uid}/bundles/{bundle_id}/tags"
        await self.db.create(collection, tag_id, fields)
        if spec.global_tag:
            bundle = await self.get_bundle(bundle_id)
            ids = list(dict.fromkeys([*(bundle.get("subscribedGlobalTagIds") or []), tag_id]))
            await self.db.patch(f"users/{uid}/bundles/{bundle_id}", {"subscribedGlobalTagIds": ids})
        return compact_document(await self._require(f"{collection}/{tag_id}")) | {
            "scope": "global" if spec.global_tag else "bundle"
        }

    async def update_tag(
        self, bundle_id: str, tag_id: str, spec: TagUpdate, *, global_tag: bool = False
    ) -> dict[str, Any]:
        scope = "tags" if global_tag else f"bundles/{bundle_id}/tags"
        path = f"{await self.user_path()}/{scope}/{tag_id}"
        current = await self._require(path)
        fields: dict[str, Any] = {}
        direct = {
            "name": spec.name,
            "defaultTag": spec.default_tag,
            "markNoteAsComplete": spec.mark_complete,
            "archiveNote": spec.archive_note,
            "swapTagIds": spec.swap_tag_ids,
        }
        fields.update({key: value for key, value in direct.items() if value is not None})
        if spec.color is not None:
            fields["color"] = hex_to_signed_color(spec.color)
        if spec.swap_tag_ids is not None:
            fields["swapTags"] = bool(spec.swap_tag_ids)
        if any(value is not None for value in (spec.task, spec.mark_complete, spec.archive_note, spec.swap_tag_ids)):
            fields["markedCompleteAction"] = 4
            next_task = spec.task if spec.task is not None else current.get("todoable", False)
            next_complete = (
                spec.mark_complete if spec.mark_complete is not None else current.get("markNoteAsComplete", False)
            )
            next_archive = spec.archive_note if spec.archive_note is not None else current.get("archiveNote", False)
            next_swaps = spec.swap_tag_ids if spec.swap_tag_ids is not None else (current.get("swapTagIds") or [])
            fields["todoable"] = bool(next_task or next_complete or next_archive or next_swaps)
        await self.db.patch(path, fields)
        return compact_document(await self._require(path)) | {"scope": "global" if global_tag else "bundle"}

    async def apply_tag(
        self, bundle_id: str, entry_id: str, tag_id: str, *, apply_actions: bool = False
    ) -> dict[str, Any]:
        entry = await self.get_entry(bundle_id, entry_id)
        tag = next((item for item in await self.list_tags(bundle_id) if item["id"] == tag_id), None)
        if tag is None:
            raise BundledNotesError("not_found", "The requested tag is not available in this bundle.")
        ids = list(entry.get("associatedTagIds") or [])
        if apply_actions and tag.get("swapTags"):
            ids = [item for item in ids if item not in (tag.get("swapTagIds") or [])]
        ids = list(dict.fromkeys([*ids, tag_id]))
        fields: dict[str, Any] = {"associatedTagIds": ids}
        if apply_actions and tag.get("todoable"):
            if tag.get("markNoteAsComplete"):
                fields["markedAsComplete"] = True
            if tag.get("archiveNote"):
                fields["archived"] = True
        path = f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"
        await self.db.patch(path, fields)
        return await self.get_entry(bundle_id, entry_id)

    async def remove_tag(self, bundle_id: str, entry_id: str, tag_id: str) -> dict[str, Any]:
        entry = await self.get_entry(bundle_id, entry_id)
        ids = [item for item in (entry.get("associatedTagIds") or []) if item != tag_id]
        path = f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"
        await self.db.patch(path, {"associatedTagIds": ids})
        return await self.get_entry(bundle_id, entry_id)

    async def delete_tag(
        self, bundle_id: str, tag_id: str, *, global_tag: bool = False, allow_dangling_references: bool = False
    ) -> dict[str, Any]:
        bundles = (
            await self.list_bundles(include_archived=True, limit=1000)
            if global_tag
            else [await self.get_bundle(bundle_id)]
        )
        references: dict[str, list[str]] = {}
        board_bundles: list[str] = []
        for bundle in bundles:
            entries = await self.list_entries(bundle["id"], include_archived=True, limit=1000)
            entry_ids = [entry["id"] for entry in entries if tag_id in (entry.get("associatedTagIds") or [])]
            if entry_ids:
                references[bundle["id"]] = entry_ids
            if tag_id in (bundle.get("kanbanColumnIds") or []):
                board_bundles.append(bundle["id"])
        if (references or board_bundles) and not allow_dangling_references:
            raise BundledNotesError(
                "tag_in_use",
                "The tag is still referenced; remove references or opt in to dangling references.",
                details={"entry_ids_by_bundle": references, "kanban_bundle_ids": board_bundles},
            )
        path = f"{await self.user_path()}/{'tags' if global_tag else f'bundles/{bundle_id}/tags'}/{tag_id}"
        await self._require(path)
        await self.db.delete(path)
        if global_tag:
            for bundle in bundles:
                subscribed = bundle.get("subscribedGlobalTagIds") or []
                if tag_id in subscribed:
                    await self.db.patch(
                        f"{await self.user_path()}/bundles/{bundle['id']}",
                        {"subscribedGlobalTagIds": [item for item in subscribed if item != tag_id]},
                    )
        return {
            "deleted": True,
            "tag_id": tag_id,
            "dangling_entry_ids_by_bundle": references,
            "dangling_kanban_bundle_ids": board_bundles,
        }

    async def configure_kanban(
        self,
        bundle_id: str,
        column_tag_ids: list[str],
        *,
        enabled: bool = True,
        backlog_name: str = "Backlog",
        hide_backlog_if_empty: bool = True,
        show_all_column: bool = False,
    ) -> dict[str, Any]:
        known = {tag["id"] for tag in await self.list_tags(bundle_id)}
        unknown = [item for item in column_tag_ids if item not in known]
        if unknown:
            raise BundledNotesError(
                "unknown_tag", "Every Kanban column must reference an available tag.", details=unknown
            )
        path = f"{await self.user_path()}/bundles/{bundle_id}"
        fields = {
            "kanbanMode": enabled,
            "kanbanColumnIds": list(dict.fromkeys(column_tag_ids)),
            "defaultColumnName": backlog_name,
            "hideBacklogColumnIfEmpty": hide_backlog_if_empty,
            "hideAllColumn": not show_all_column,
        }
        await self.db.patch(path, fields)
        return await self.get_bundle(bundle_id)

    async def move_kanban(self, bundle_id: str, entry_id: str, target_column_tag_id: str | None) -> dict[str, Any]:
        bundle, entry = await asyncio.gather(self.get_bundle(bundle_id), self.get_entry(bundle_id, entry_id))
        columns = bundle.get("kanbanColumnIds") or []
        if target_column_tag_id is not None and target_column_tag_id not in columns:
            raise BundledNotesError("unknown_column", "The target is not a configured Kanban column.")
        tags = [tag for tag in (entry.get("associatedTagIds") or []) if tag not in columns]
        if target_column_tag_id:
            tags.append(target_column_tag_id)
        path = f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}"
        await self.db.patch(path, {"associatedTagIds": tags})
        return await self.get_entry(bundle_id, entry_id)

    async def list_templates(self, limit: int = 300) -> list[dict[str, Any]]:
        rows = await self.db.list(f"{await self.user_path()}/templates", page_size=limit)
        return [compact_document(row) for row in rows]

    async def create_template(
        self, bundle_id: str, name: str, description: str = "", include_entries: bool = False
    ) -> dict[str, Any]:
        uid, template_id = await self.uid(), new_id()
        bundle = await self.get_bundle(bundle_id)
        fields = {key: value for key, value in bundle.items() if key not in {"id", "archived", "_path"}}
        fields.update({"id": template_id, "ownerId": uid, "name": name, "description": description})
        await self.db.create(f"users/{uid}/templates", template_id, fields)
        for tag in await self.list_tags(bundle_id, include_global=False):
            copied = {
                key: value
                for key, value in tag.items()
                if key not in {"_path", "_create_time", "_update_time", "scope", "colorHex"}
            }
            await self.db.create(f"users/{uid}/templates/{template_id}/tags", tag["id"], copied)
        if include_entries:
            for entry in await self.list_entries(bundle_id, include_archived=True, limit=1000):
                copied = {key: value for key, value in entry.items() if not key.startswith("_")}
                await self.db.create(f"users/{uid}/templates/{template_id}/entries", entry["id"], copied)
        return compact_document(await self._require(f"users/{uid}/templates/{template_id}"))

    async def apply_template(
        self, template_id: str, *, name: str | None = None, default_bundle: bool = False
    ) -> dict[str, Any]:
        uid, bundle_id = await self.uid(), new_id()
        template = await self._require(f"users/{uid}/templates/{template_id}")
        fields = {key: value for key, value in template.items() if not key.startswith("_") and key != "id"}
        fields.update({"id": bundle_id, "ownerId": uid, "archived": False})
        if name:
            fields["name"] = name
        await self.db.create(f"users/{uid}/bundles", bundle_id, fields)
        for subcollection in ("tags", "entries"):
            for row in await self.db.list(f"users/{uid}/templates/{template_id}/{subcollection}"):
                copied = {key: value for key, value in row.items() if not key.startswith("_")}
                if subcollection == "entries":
                    copied["parentBundleId"] = bundle_id
                await self.db.create(f"users/{uid}/bundles/{bundle_id}/{subcollection}", row["id"], copied)
        if default_bundle:
            await self.db.patch(f"users/{uid}", {"defaultBundle": bundle_id})
        return await self.get_bundle(bundle_id)

    async def delete_template(self, template_id: str) -> dict[str, Any]:
        uid, base = await self.uid(), f"users/{await self.uid()}/templates/{template_id}"
        template = await self._require(base)
        counts: dict[str, int] = {}
        for subcollection in ("entries", "tags"):
            rows = await self.db.list(f"{base}/{subcollection}")
            counts[subcollection] = len(rows)
            for row in rows:
                await self.db.delete(f"{base}/{subcollection}/{row['id']}")
        await self.db.delete(base)
        return {"deleted": True, "template_id": template_id, "name": template.get("name"), **counts, "uid": uid}

    async def list_attachments(self, limit: int = 300) -> list[dict[str, Any]]:
        rows = await self.db.list(f"{await self.user_path()}/attachments", page_size=limit)
        return [compact_document(row) for row in rows]

    async def upload_attachment(self, bundle_id: str, entry_id: str, file_path: str) -> dict[str, Any]:
        uid, attachment_id = await self.uid(), new_id()
        entry = await self.get_entry(bundle_id, entry_id)
        path, filename, file_size = await asyncio.to_thread(_file_info, file_path)
        object_name = f"users/{uid}/{attachment_id}"
        catalog_path = f"users/{uid}/attachments/{attachment_id}"
        entry_path = f"users/{uid}/bundles/{bundle_id}/entries/{entry_id}"
        metadata = {
            "targetBundleId": bundle_id,
            "filename": filename,
            "associatedTagIds": ",".join(entry.get("associatedTagIds") or []),
            "targetEntryId": entry_id,
        }
        record = {
            "id": attachment_id,
            "type": ATTACHMENT_TYPES["file_account"],
            "uid": attachment_id,
            "storageId": attachment_id,
            "fileSize": file_size,
            "text": filename,
        }
        original_attachments = dict(entry.get("attachments") or {})
        next_attachments = dict(original_attachments)
        next_attachments[attachment_id] = {key: value for key, value in record.items() if key != "id"}
        uploaded = False
        entry_updated = False
        try:
            uploaded_metadata = await self.storage.upload(object_name, str(path), metadata)
            uploaded = True
            _verify_storage_attachment(uploaded_metadata, object_name, file_size, metadata)
            try:
                await self.db.create(f"users/{uid}/attachments", attachment_id, record)
            except BundledNotesError as error:
                if error.code != "conflict":
                    raise
                await self.db.patch(catalog_path, record)
            await self.db.patch(entry_path, {"attachments": next_attachments})
            entry_updated = True

            catalog = compact_document(await self._require(catalog_path))
            if not _attachment_record_matches(catalog, record):
                await self.db.patch(catalog_path, record)
                catalog = compact_document(await self._require(catalog_path))
            if not _attachment_record_matches(catalog, record):
                raise BundledNotesError(
                    "attachment_verification_failed",
                    "The uploaded file catalog metadata could not be verified.",
                )
        except Exception:
            if entry_updated:
                await self.db.patch(entry_path, {"attachments": original_attachments})
            await self.db.delete(catalog_path)
            if uploaded:
                await self.storage.delete(object_name)
            raise
        return {"attachment": catalog, "entry": await self.get_entry(bundle_id, entry_id)}

    async def remove_attachment(self, bundle_id: str, entry_id: str, attachment_id: str) -> dict[str, Any]:
        entry = await self.get_entry(bundle_id, entry_id)
        attachments = dict(entry.get("attachments") or {})
        if attachment_id not in attachments:
            raise BundledNotesError("not_found", "The entry does not contain this attachment.")
        attachments.pop(attachment_id)
        await self.db.patch(
            f"{await self.user_path()}/bundles/{bundle_id}/entries/{entry_id}", {"attachments": attachments}
        )
        return await self.get_entry(bundle_id, entry_id)

    async def delete_account_attachment(self, attachment_id: str) -> dict[str, Any]:
        uid = await self.uid()
        record = await self._require(f"users/{uid}/attachments/{attachment_id}")
        await self.storage.delete(f"users/{uid}/{record.get('storageId', attachment_id)}")
        await self.db.delete(f"users/{uid}/attachments/{attachment_id}")
        return {"deleted": True, "attachment_id": attachment_id, "filename": record.get("text")}

    async def _copy_entry(
        self, source: dict[str, Any], target_bundle_id: str, target_tag_ids: list[str] | None
    ) -> dict[str, Any]:
        uid, new_entry_id = await self.uid(), new_id()
        fields = {
            key: value for key, value in source.items() if not key.startswith("_") and key not in {"id", "numericId"}
        }
        fields.update(
            {
                "id": new_entry_id,
                "numericId": new_numeric_id(),
                "parentBundleId": target_bundle_id,
                "associatedTagIds": list(dict.fromkeys(target_tag_ids or [])),
            }
        )
        await self.db.create(f"users/{uid}/bundles/{target_bundle_id}/entries", new_entry_id, fields)
        return await self.get_entry(target_bundle_id, new_entry_id)

    async def _require(self, path: str) -> dict[str, Any]:
        result = await self.db.get(path, missing_ok=True)
        if result is None:
            raise BundledNotesError("not_found", "The requested Bundled Notes document was not found.", status_code=404)
        return result

    @staticmethod
    def _bundle_defaults(uid: str, bundle_id: str, spec: BundleCreate) -> dict[str, Any]:
        board = spec.template == "board"
        return {
            "id": bundle_id,
            "ownerId": uid,
            "name": spec.name,
            "description": spec.description,
            "archived": False,
            "indexPosition": 0,
            "contentNameSingle": "",
            "contentNamePlural": "",
            "entriesLayoutType": 2,
            "entriesLayoutTypeWeb": 1 if spec.template == "notes" else 2,
            "bundleEntrySortMethod": SORT_METHODS["updated_newest"],
            "subscribedGlobalTagIds": [],
            "tagPriorityOrder": [],
            "kanbanMode": board,
            "kanbanColumnIds": [],
            "defaultColumnName": "Backlog",
            "hideBacklogColumnIfEmpty": True,
            "hideAllColumn": board,
            "collapsedBoardColumns": [],
            "compactTags": False,
            "numberedList": False,
            "showLastEditedTime": False,
            "showCreationDate": True,
            "colourfulBackgrounds": False,
            "richColourfulBackgrounds": False,
            "hideFirstTag": False,
            "numberOfLinesForPreview": 3,
            "numberOfAttachmentsForPreview": 2,
            "keepCompleteItemsAtBottom": True,
            "groupTagsTogether": False,
            "orderByRemindersFirst": True,
            "config": {"markdownFlavor": "legacy", "lockEditorByDefault": False, "showEllipsisIfNoteIsHidden": False},
        }


def _file_info(file_path: str) -> tuple[Path, str, int]:
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise BundledNotesError("file_not_found", "The local attachment file does not exist.")
    return path, path.name, path.stat().st_size


def _verify_storage_attachment(
    uploaded: dict[str, Any], object_name: str, file_size: int, custom_metadata: dict[str, str]
) -> None:
    try:
        uploaded_size = int(uploaded.get("size"))
    except (TypeError, ValueError) as error:
        raise BundledNotesError(
            "attachment_verification_failed", "The uploaded file size could not be verified."
        ) from error
    if uploaded.get("name") != object_name or uploaded_size != file_size:
        raise BundledNotesError(
            "attachment_verification_failed", "The uploaded file metadata did not match the requested file."
        )
    stored_metadata = uploaded.get("metadata")
    if not isinstance(stored_metadata, dict) or any(
        stored_metadata.get(key) != value for key, value in custom_metadata.items()
    ):
        raise BundledNotesError(
            "attachment_verification_failed", "The uploaded file metadata did not match the requested file."
        )


def _attachment_record_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())
