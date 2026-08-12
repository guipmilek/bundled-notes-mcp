from __future__ import annotations

import secrets
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
MAX_FILE_BYTES = 400 * 1024 * 1024
MAX_MCP_DOWNLOAD_BYTES = 10 * 1024 * 1024

SORT_METHODS = {
    "alphabetical": 0,
    "alphabetical_reverse": 1,
    "updated_oldest": 2,
    "updated_newest": 3,
    "managed_order": 4,
    "created_oldest": 5,
    "created_newest": 6,
}
LAYOUTS = {"compact": 0, "grid": 1, "standard": 2}
ENTRY_TYPES = {"solo": -17, "mixed": -12, "solo_image": -23}
ATTACHMENT_TYPES = {
    "rich_link_preview": 1,
    "arbitrary_text": 99,
    "reminder_text": 102,
    "image_url": 32,
    "image_account": 17,
    "image_device": 18,
    "file_account": 6,
    "file_device": 5,
}


def new_id(length: int = 16) -> str:
    return "".join(secrets.choice(ID_ALPHABET) for _ in range(length))


def new_numeric_id() -> int:
    return secrets.randbelow(10_000_000)


def hex_to_signed_color(value: str) -> int:
    clean = value.strip().lstrip("#")
    if len(clean) == 6:
        clean = "ff" + clean
    if len(clean) != 8:
        raise ValueError("color must be #RRGGBB or #AARRGGBB")
    number = int(clean, 16)
    return number - 2**32 if number >= 2**31 else number


def signed_color_to_hex(value: int) -> str:
    return f"#{value & 0xFFFFFF:06x}"


class BundleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    template: Literal["notes", "list", "board"] = "list"
    default_bundle: bool = False


class BundleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    content_name_single: str | None = Field(default=None, max_length=100)
    content_name_plural: str | None = Field(default=None, max_length=100)
    markdown_flavor: Literal["legacy", "gfm"] | None = None
    layout: Literal["compact", "grid", "standard"] | None = None
    sort_method: (
        Literal[
            "alphabetical",
            "alphabetical_reverse",
            "updated_oldest",
            "updated_newest",
            "managed_order",
            "created_oldest",
            "created_newest",
        ]
        | None
    ) = None
    background: Literal["none", "tinted", "rich"] | None = None
    compact_tags: bool | None = None
    numbered_list: bool | None = None
    show_creation_date: bool | None = None
    show_last_edited_time: bool | None = None
    hide_first_tag: bool | None = None
    preview_lines: int | None = Field(default=None, ge=0, le=100)
    preview_attachments: int | None = Field(default=None, ge=0, le=100)
    keep_complete_at_bottom: bool | None = None
    group_tags_together: bool | None = None
    order_reminders_first: bool | None = None
    default_bundle: bool | None = None


class EntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="", max_length=5000)
    content: str = Field(default="", max_length=2_000_000)
    tag_ids: list[str] = Field(default_factory=list, max_length=200)
    pinned: bool = False
    archived: bool = False
    completed: bool = False


class EntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=5000)
    content: str | None = Field(default=None, max_length=2_000_000)
    tag_ids: list[str] | None = Field(default=None, max_length=200)
    pinned: bool | None = None


class TagCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    color: str = "#00bfa5"
    default_tag: bool = False
    task: bool = False
    mark_complete: bool = False
    archive_note: bool = False
    swap_tag_ids: list[str] = Field(default_factory=list, max_length=200)
    global_tag: bool = False

    @field_validator("color")
    @classmethod
    def valid_color(cls, value: str) -> str:
        hex_to_signed_color(value)
        return value


class TagUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    color: str | None = None
    default_tag: bool | None = None
    task: bool | None = None
    mark_complete: bool | None = None
    archive_note: bool | None = None
    swap_tag_ids: list[str] | None = Field(default=None, max_length=200)

    @field_validator("color")
    @classmethod
    def valid_color(cls, value: str | None) -> str | None:
        if value is not None:
            hex_to_signed_color(value)
        return value


def compact_document(value: dict[str, Any]) -> dict[str, Any]:
    result = {key: item for key, item in value.items() if not key.startswith("_")}
    if not result.get("id") and value.get("_path"):
        result["id"] = str(value["_path"]).rsplit("/", 1)[-1]
    if isinstance(result.get("color"), int):
        result["colorHex"] = signed_color_to_hex(result["color"])
    return result
