from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from bundled_notes_mcp.models import (
    ATTACHMENT_TYPES,
    ENTRY_TYPES,
    LAYOUTS,
    SORT_METHODS,
    BundleCreate,
    BundleUpdate,
    EntryCreate,
    TagCreate,
    compact_document,
    hex_to_signed_color,
    new_id,
    new_numeric_id,
    signed_color_to_hex,
)


def test_generated_id_is_web_compatible() -> None:
    values = {new_id() for _ in range(100)}
    assert len(values) == 100
    assert all(re.fullmatch(r"[0-9A-Za-z]{16}", value) for value in values)


def test_numeric_id_range() -> None:
    assert all(0 <= new_numeric_id() < 10_000_000 for _ in range(100))


@pytest.mark.parametrize(
    ("value", "encoded", "roundtrip"),
    [("#00bfa5", -16728155, "#00bfa5"), ("#ff0000", -65536, "#ff0000"), ("#80ffffff", -2130706433, "#ffffff")],
)
def test_color_conversion(value: str, encoded: int, roundtrip: str) -> None:
    assert hex_to_signed_color(value) == encoded
    assert signed_color_to_hex(encoded) == roundtrip


@pytest.mark.parametrize("value", ["red", "#12", "#12345g", "#123456789"])
def test_invalid_color(value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        TagCreate(name="x", color=value)


def test_bundle_and_entry_validation() -> None:
    assert BundleCreate(name="Work").template == "list"
    assert EntryCreate().tag_ids == []
    with pytest.raises(ValidationError):
        BundleCreate(name="")
    with pytest.raises(ValidationError):
        BundleUpdate(preview_lines=101)


def test_observed_enums_are_stable() -> None:
    assert list(SORT_METHODS.values()) == [0, 1, 2, 3, 4, 5, 6]
    assert LAYOUTS == {"compact": 0, "grid": 1, "standard": 2}
    assert ENTRY_TYPES == {"solo": -17, "mixed": -12, "solo_image": -23}
    assert ATTACHMENT_TYPES["file_account"] == 6
    assert ATTACHMENT_TYPES["reminder_text"] == 102


def test_missing_legacy_id_is_derived_from_path() -> None:
    assert compact_document({"_path": "users/u/attachments/legacy", "text": "file"}) == {
        "id": "legacy",
        "text": "file",
    }
