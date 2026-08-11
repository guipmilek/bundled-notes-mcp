from __future__ import annotations

from typing import Any


class BundledNotesError(RuntimeError):
    """A sanitized, actionable Bundled Notes error."""

    def __init__(self, code: str, message: str, *, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

    def public(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.status_code is not None:
            value["status_code"] = self.status_code
        if self.details is not None:
            value["details"] = self.details
        return value


def public_error(error: Exception) -> dict[str, Any]:
    if isinstance(error, BundledNotesError):
        return error.public()
    return {"code": "unexpected_error", "message": "Unexpected Bundled Notes MCP error."}
