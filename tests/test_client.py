from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

import pytest

from bundled_notes_mcp.client import BundledNotesClient
from bundled_notes_mcp.errors import BundledNotesError
from bundled_notes_mcp.models import BundleCreate, EntryCreate, EntryUpdate, TagCreate


class FakeAuth:
    settings = SimpleNamespace(storage_bucket="bucket", project_id="project")
    http = None

    async def token(self) -> SimpleNamespace:
        return SimpleNamespace(uid="u")


class MemoryDB:
    def __init__(self) -> None:
        self.docs: dict[str, dict[str, Any]] = {
            "users/u": {
                "id": "u",
                "purchaseToken": "hidden",
                "settings": {"automaticallyFetchLinkPreviews": True, "futureSecret": "hidden"},
            }
        }

    async def get(self, path: str, *, missing_ok: bool = False) -> dict[str, Any] | None:
        value = self.docs.get(path)
        if value is None and not missing_ok:
            raise BundledNotesError("not_found", "missing")
        return copy.deepcopy(value)

    async def list(self, path: str, *, page_size: int = 300) -> list[dict[str, Any]]:
        prefix = f"{path}/"
        rows = []
        for key, value in self.docs.items():
            tail = key.removeprefix(prefix)
            if key.startswith(prefix) and "/" not in tail:
                rows.append(copy.deepcopy(value))
        return rows[:page_size]

    async def create(self, collection: str, document_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        path = f"{collection}/{document_id}"
        if path in self.docs:
            raise BundledNotesError("conflict", "exists")
        self.docs[path] = copy.deepcopy(fields)
        return copy.deepcopy(fields)

    async def patch(self, path: str, fields: dict[str, Any]) -> dict[str, Any]:
        if path not in self.docs:
            raise BundledNotesError("not_found", "missing")
        self.docs[path].update(copy.deepcopy(fields))
        return copy.deepcopy(self.docs[path])

    async def delete(self, path: str) -> None:
        self.docs.pop(path, None)


@pytest.fixture
def api() -> BundledNotesClient:
    client = BundledNotesClient(FakeAuth())  # type: ignore[arg-type]
    client.db = MemoryDB()  # type: ignore[assignment]
    return client


@pytest.mark.asyncio
async def test_current_user_redacts_purchase_token(api: BundledNotesClient) -> None:
    user = await api.current_user()
    assert user["uid"] == "u"
    assert "purchaseToken" not in user
    assert user["settings"] == {"automaticallyFetchLinkPreviews": True}


@pytest.mark.asyncio
@pytest.mark.parametrize("template", ["notes", "list", "board"])
async def test_create_bundle_templates(api: BundledNotesClient, template: str) -> None:
    bundle = await api.create_bundle(BundleCreate(name=f"{template} bundle", template=template))  # type: ignore[arg-type]
    assert bundle["name"] == f"{template} bundle"
    assert bundle["kanbanMode"] is (template == "board")
    tags = await api.list_tags(bundle["id"], include_global=False)
    assert len(tags) == ({"notes": 1, "list": 0, "board": 3}[template])
    if template == "board":
        assert len((await api.get_bundle(bundle["id"]))["kanbanColumnIds"]) == 3


@pytest.mark.asyncio
async def test_entry_crud_and_search(api: BundledNotesClient) -> None:
    bundle = await api.create_bundle(BundleCreate(name="Work"))
    entry = await api.create_entry(bundle["id"], EntryCreate(title="Alpha", content="needle markdown"))
    assert entry["deviceName"] == "bundled-notes-mcp"
    updated = await api.update_entry(bundle["id"], entry["id"], EntryUpdate(title="Beta", pinned=True))
    assert updated["title"] == "Beta"
    assert updated["pinned"] is True
    assert len(await api.search("NEEDLE")) == 1
    assert await api.search("absent") == []
    deleted = await api.delete_entry(bundle["id"], entry["id"])
    assert deleted["deleted"] is True


@pytest.mark.asyncio
async def test_duplicate_and_move_semantics(api: BundledNotesClient) -> None:
    source = await api.create_bundle(BundleCreate(name="Source"))
    target = await api.create_bundle(BundleCreate(name="Target"))
    entry = await api.create_entry(source["id"], EntryCreate(title="Move me", tag_ids=["source-tag"]))
    copied = await api.duplicate_entry(source["id"], entry["id"], target["id"], ["destination-tag"])
    assert copied["id"] != entry["id"]
    assert copied["associatedTagIds"] == ["destination-tag"]
    assert (await api.get_entry(source["id"], entry["id"]))["title"] == "Move me"
    moved = await api.move_entry(source["id"], entry["id"], target["id"], [])
    assert moved["parentBundleId"] == target["id"]
    with pytest.raises(BundledNotesError):
        await api.get_entry(source["id"], entry["id"])


@pytest.mark.asyncio
async def test_task_tag_actions_and_reference_guard(api: BundledNotesClient) -> None:
    bundle = await api.create_bundle(BundleCreate(name="Tasks"))
    tag = await api.create_tag(bundle["id"], TagCreate(name="Done", task=True, mark_complete=True))
    entry = await api.create_entry(bundle["id"], EntryCreate(title="Task"))
    applied = await api.apply_tag(bundle["id"], entry["id"], tag["id"], apply_actions=True)
    assert applied["markedAsComplete"] is True
    assert applied["associatedTagIds"] == [tag["id"]]
    with pytest.raises(BundledNotesError) as raised:
        await api.delete_tag(bundle["id"], tag["id"])
    assert raised.value.code == "tag_in_use"
    removed = await api.remove_tag(bundle["id"], entry["id"], tag["id"])
    assert removed["associatedTagIds"] == []
    assert (await api.delete_tag(bundle["id"], tag["id"]))["deleted"] is True


@pytest.mark.asyncio
async def test_tag_swap_runs_only_when_actions_requested(api: BundledNotesClient) -> None:
    bundle = await api.create_bundle(BundleCreate(name="Swaps"))
    old = await api.create_tag(bundle["id"], TagCreate(name="Old"))
    new = await api.create_tag(bundle["id"], TagCreate(name="New", task=True, swap_tag_ids=[old["id"]]))
    first = await api.create_entry(bundle["id"], EntryCreate(title="First", tag_ids=[old["id"]]))
    normal = await api.apply_tag(bundle["id"], first["id"], new["id"], apply_actions=False)
    assert normal["associatedTagIds"] == [old["id"], new["id"]]
    second = await api.create_entry(bundle["id"], EntryCreate(title="Second", tag_ids=[old["id"]]))
    action = await api.apply_tag(bundle["id"], second["id"], new["id"], apply_actions=True)
    assert action["associatedTagIds"] == [new["id"]]


@pytest.mark.asyncio
async def test_global_tag_delete_checks_all_bundles_and_unsubscribes(api: BundledNotesClient) -> None:
    first = await api.create_bundle(BundleCreate(name="First"))
    second = await api.create_bundle(BundleCreate(name="Second"))
    tag = await api.create_tag(first["id"], TagCreate(name="Global", global_tag=True))
    await api.db.patch(f"users/u/bundles/{second['id']}", {"subscribedGlobalTagIds": [tag["id"]]})
    entry = await api.create_entry(second["id"], EntryCreate(title="Reference", tag_ids=[tag["id"]]))
    with pytest.raises(BundledNotesError) as raised:
        await api.delete_tag(first["id"], tag["id"], global_tag=True)
    assert raised.value.details["entry_ids_by_bundle"] == {second["id"]: [entry["id"]]}
    deleted = await api.delete_tag(first["id"], tag["id"], global_tag=True, allow_dangling_references=True)
    assert deleted["deleted"] is True
    assert tag["id"] not in (await api.get_bundle(first["id"]))["subscribedGlobalTagIds"]
    assert tag["id"] not in (await api.get_bundle(second["id"]))["subscribedGlobalTagIds"]


@pytest.mark.asyncio
async def test_kanban_preserves_non_column_tags(api: BundledNotesClient) -> None:
    bundle = await api.create_bundle(BundleCreate(name="Board", template="board"))
    columns = bundle["kanbanColumnIds"]
    other = await api.create_tag(bundle["id"], TagCreate(name="Priority"))
    entry = await api.create_entry(bundle["id"], EntryCreate(title="Card", tag_ids=[columns[0], other["id"]]))
    moved = await api.move_kanban(bundle["id"], entry["id"], columns[1])
    assert moved["associatedTagIds"] == [other["id"], columns[1]]
    backlog = await api.move_kanban(bundle["id"], entry["id"], None)
    assert backlog["associatedTagIds"] == [other["id"]]


@pytest.mark.asyncio
async def test_template_roundtrip_and_recursive_delete(api: BundledNotesClient) -> None:
    bundle = await api.create_bundle(BundleCreate(name="Template source"))
    await api.create_tag(bundle["id"], TagCreate(name="Tag"))
    await api.create_entry(bundle["id"], EntryCreate(title="Included"))
    template = await api.create_template(bundle["id"], "Reusable", include_entries=True)
    applied = await api.apply_template(template["id"], name="Applied")
    assert applied["name"] == "Applied"
    assert len(await api.list_entries(applied["id"])) == 1
    template_deleted = await api.delete_template(template["id"])
    assert template_deleted["entries"] == 1
    bundle_deleted = await api.delete_bundle(applied["id"])
    assert bundle_deleted["deleted_entries"] == 1
    assert bundle_deleted["deleted_tags"] == 1
