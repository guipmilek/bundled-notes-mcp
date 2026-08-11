from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

SCHEMA_CONTRACT_VERSION = 1

# The contract deliberately describes shapes, never values. Unknown fields are
# reported as additive drift and remain compatible; missing identity fields or
# changed wire types are breaking drift.
CONTRACTS: dict[str, dict[str, Any]] = {
    "user": {
        "required": {"defaultBundle", "storageUsedInBytes"},
        "fields": {
            "accountOnHold": {"boolean"},
            "acceptedPrivacyPolicyVersion": {"integer"},
            "defaultBundle": {"string", "null"},
            "id": {"string"},
            "numberOfArchivedBundles": {"integer"},
            "numberOfBundles": {"integer"},
            "proSubscriber": {"boolean"},
            "seenChangelogVersion": {"integer"},
            "settings": {"map"},
            "settings.automaticallyFetchLinkPreviews": {"boolean"},
            "settings.seenWebAppChangeLogVersion": {"integer"},
            "storageLeftInBytes": {"integer"},
            "storageUsedInBytes": {"integer"},
            "subscriptionExpiryTime": {"integer"},
            "subscriptionMethod": {"string"},
            "subscriptionSku": {"string"},
        },
    },
    "bundle": {
        "required": {"id", "ownerId", "name"},
        "fields": {
            "archived": {"boolean"},
            "bundleEntrySortMethod": {"integer"},
            "collapsedBoardColumns": {"array", "null"},
            "colourfulBackgrounds": {"boolean"},
            "compactTags": {"boolean"},
            "config": {"map"},
            "config.lockEditorByDefault": {"boolean"},
            "config.markdownFlavor": {"string"},
            "config.showEllipsisIfNoteIsHidden": {"boolean"},
            "contentNamePlural": {"string", "null"},
            "contentNameSingle": {"string", "null"},
            "defaultColumnName": {"string", "null"},
            "description": {"string", "null"},
            "entriesLayoutType": {"integer"},
            "entriesLayoutTypeWeb": {"integer"},
            "groupTagsTogether": {"boolean"},
            "hideAllColumn": {"boolean"},
            "hideBacklogColumnIfEmpty": {"boolean"},
            "hideFirstTag": {"boolean"},
            "id": {"string"},
            "indexPosition": {"integer"},
            "kanbanColumnIds": {"array", "null"},
            "kanbanMode": {"boolean"},
            "keepCompleteItemsAtBottom": {"boolean"},
            "name": {"string"},
            "numberOfAttachmentsForPreview": {"integer"},
            "numberOfEntries": {"integer"},
            "numberOfLinesForPreview": {"integer"},
            "numberedList": {"boolean"},
            "orderByRemindersFirst": {"boolean"},
            "ownerId": {"string"},
            "richColourfulBackgrounds": {"boolean"},
            "showCreationDate": {"boolean"},
            "showLastEditedTime": {"boolean"},
            "subscribedGlobalTagIds": {"array", "null"},
            "tagPriorityOrder": {"array", "null"},
        },
    },
    "entry": {
        "required": {"id", "parentBundleId", "title", "content"},
        "fields": {
            "archived": {"boolean"},
            "associatedTagIds": {"array", "null"},
            "attachments": {"map", "null"},
            "attachments.*.fileSize": {"integer"},
            "attachments.*.storageId": {"string"},
            "attachments.*.text": {"string"},
            "attachments.*.type": {"integer"},
            "attachments.*.uid": {"string"},
            "content": {"string"},
            "createdTime": {"integer"},
            "deviceName": {"string"},
            "id": {"string"},
            "indexPosition": {"integer"},
            "lastEditedTime": {"integer"},
            "markedAsComplete": {"boolean"},
            "numericId": {"integer"},
            "parentBundleId": {"string"},
            "pinned": {"boolean"},
            "title": {"string"},
            "type": {"integer"},
        },
    },
    "tag": {
        "required": {"id", "name", "color"},
        "fields": {
            "archiveNote": {"boolean"},
            "bundleId": {"string"},
            "color": {"integer"},
            "defaultTag": {"boolean"},
            "id": {"string"},
            "indexPosition": {"integer"},
            "markNoteAsComplete": {"boolean"},
            "markedCompleteAction": {"integer"},
            "name": {"string"},
            "swapTagIds": {"array", "null"},
            "swapTags": {"boolean"},
            "todoable": {"boolean"},
        },
    },
    "template": {"inherits": "bundle", "required": {"id", "ownerId", "name"}},
    "attachment": {
        "required": {"id", "storageId", "type", "fileSize", "text"},
        "fields": {
            "fileSize": {"integer"},
            "id": {"string"},
            "storageId": {"string"},
            "text": {"string"},
            "type": {"integer"},
            "uid": {"string"},
        },
    },
}

_IGNORED_FIELDS = {"_path", "_create_time", "_update_time"}
_SENSITIVE_FIELD_MARKERS = {"token", "password", "secret", "credential"}
_DYNAMIC_MAPS = {("entry", "attachments")}


def build_schema_report(samples: dict[str, Iterable[dict[str, Any]]]) -> dict[str, Any]:
    collections: dict[str, Any] = {}
    has_breaking = False
    has_additive = False

    for kind in CONTRACTS:
        documents = list(samples.get(kind, []))
        observed = observe_documents(kind, documents)
        contract = _resolved_contract(kind)
        required = set(contract.get("required", set()))
        expected = contract.get("fields", {})
        missing_required = sorted(required - observed.keys()) if documents else []
        unknown_fields = sorted(observed.keys() - expected.keys())
        incompatible: list[dict[str, Any]] = []
        for field in sorted(observed.keys() & expected.keys()):
            rejected = sorted(item for item in observed[field] if not _accepted(item, expected[field]))
            if rejected:
                incompatible.append({"field": field, "observed": rejected, "expected": sorted(expected[field])})
        has_breaking = has_breaking or bool(missing_required or incompatible)
        has_additive = has_additive or bool(unknown_fields)
        collections[kind] = {
            "sample_count": len(documents),
            "state": "unobserved" if not documents else "observed",
            "fields": {field: sorted(types) for field, types in sorted(observed.items())},
            "unknown_fields": unknown_fields,
            "missing_required_fields": missing_required,
            "incompatible_fields": incompatible,
        }

    fingerprint_shape = {
        kind: {"state": value["state"], "fields": value["fields"]} for kind, value in collections.items()
    }
    canonical = json.dumps(fingerprint_shape, sort_keys=True, separators=(",", ":"))
    status = "breaking_drift" if has_breaking else "additive_drift" if has_additive else "compatible"
    return {
        "schema_contract_version": SCHEMA_CONTRACT_VERSION,
        "compatible": not has_breaking,
        "status": status,
        "fingerprint": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "privacy": "field names and value types only; document values are never returned",
        "collections": collections,
    }


def observe_documents(kind: str, documents: Iterable[dict[str, Any]]) -> dict[str, set[str]]:
    fields: dict[str, set[str]] = {}
    for document in documents:
        for key, value in document.items():
            if key in _IGNORED_FIELDS or _sensitive_field(key):
                continue
            _observe_value(kind, key, value, fields)
    return fields


def _observe_value(kind: str, path: str, value: Any, fields: dict[str, set[str]]) -> None:
    fields.setdefault(path, set()).add(_value_type(value))
    if not isinstance(value, dict):
        return
    if (kind, path) in _DYNAMIC_MAPS:
        for item in value.values():
            if isinstance(item, dict):
                for key, nested in item.items():
                    if _sensitive_field(key):
                        continue
                    _observe_value(kind, f"{path}.*.{key}", nested, fields)
        return
    for key, nested in value.items():
        if _sensitive_field(key):
            continue
        _observe_value(kind, f"{path}.{key}", nested, fields)


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "map"
    return type(value).__name__


def _resolved_contract(kind: str) -> dict[str, Any]:
    contract = CONTRACTS[kind]
    parent = contract.get("inherits")
    if not parent:
        return contract
    base = _resolved_contract(parent)
    return {
        "required": set(base.get("required", set())) | set(contract.get("required", set())),
        "fields": dict(base.get("fields", {})) | dict(contract.get("fields", {})),
    }


def _accepted(observed: str, expected: set[str]) -> bool:
    return observed in expected


def _sensitive_field(field: str) -> bool:
    lowered = field.casefold()
    return any(marker in lowered for marker in _SENSITIVE_FIELD_MARKERS)
