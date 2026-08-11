from __future__ import annotations

from bundled_notes_mcp.schema import build_schema_report, observe_documents


def test_schema_report_never_contains_document_values() -> None:
    secret = "private note body that must never leave the probe"
    report = build_schema_report(
        {
            "entry": [
                {
                    "id": "entry-id",
                    "parentBundleId": "bundle-id",
                    "title": "Private title",
                    "content": secret,
                    "attachments": {
                        "dynamic-secret-id": {
                            "uid": "dynamic-secret-id",
                            "storageId": "dynamic-secret-id",
                            "text": "private-filename.txt",
                            "fileSize": 49,
                            "type": 6,
                        }
                    },
                }
            ],
            "user": [{"id": "u", "purchaseToken": "never expose this", "storageUsedInBytes": 0}],
        }
    )

    serialized = str(report)
    assert secret not in serialized
    assert "Private title" not in serialized
    assert "private-filename.txt" not in serialized
    assert "dynamic-secret-id" not in serialized
    assert "purchaseToken" not in serialized
    assert report["collections"]["entry"]["fields"]["attachments.*.fileSize"] == ["integer"]


def test_additive_fields_are_reported_without_breaking_compatibility() -> None:
    report = build_schema_report(
        {
            "attachment": [
                {
                    "id": "a",
                    "storageId": "a",
                    "type": 6,
                    "fileSize": 1,
                    "text": "x",
                    "futureField": True,
                }
            ]
        }
    )

    assert report["compatible"] is True
    assert report["status"] == "additive_drift"
    assert report["collections"]["attachment"]["unknown_fields"] == ["futureField"]


def test_missing_required_or_changed_type_is_breaking_drift() -> None:
    report = build_schema_report(
        {"attachment": [{"id": "a", "storageId": "a", "type": "file", "fileSize": 1, "text": "x"}]}
    )

    assert report["compatible"] is False
    assert report["status"] == "breaking_drift"
    assert report["collections"]["attachment"]["incompatible_fields"] == [
        {"field": "type", "observed": ["string"], "expected": ["integer"]}
    ]


def test_legacy_null_arrays_are_accepted() -> None:
    observed = observe_documents(
        "bundle",
        [
            {
                "id": "b",
                "ownerId": "u",
                "name": "Legacy",
                "kanbanColumnIds": None,
                "subscribedGlobalTagIds": None,
            }
        ],
    )
    assert observed["kanbanColumnIds"] == {"null"}
    assert observed["subscribedGlobalTagIds"] == {"null"}
    assert (
        build_schema_report(
            {
                "bundle": [
                    {
                        "id": "b",
                        "ownerId": "u",
                        "name": "Legacy",
                        **{"kanbanColumnIds": None, "subscribedGlobalTagIds": None},
                    }
                ]
            }
        )["compatible"]
        is True
    )


def test_fingerprint_depends_on_shape_not_sample_count() -> None:
    attachment = {"id": "a", "storageId": "a", "type": 6, "fileSize": 1, "text": "x"}
    one = build_schema_report({"attachment": [attachment]})
    two = build_schema_report({"attachment": [attachment, attachment]})
    assert one["fingerprint"] == two["fingerprint"]
