from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import BundledNotesError

DEFAULT_PROJECT_ID = "bundled-7946c"
DEFAULT_STORAGE_BUCKET = "bundled-7946c.appspot.com"
WEB_ORIGIN = "https://bundlednotes.app"


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    refresh_token: str
    project_id: str = DEFAULT_PROJECT_ID
    storage_bucket: str = DEFAULT_STORAGE_BUCKET
    expected_uid: str | None = None
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(override=False)
        api_key = os.getenv("BUNDLED_FIREBASE_API_KEY", "").strip()
        refresh_token = os.getenv("BUNDLED_FIREBASE_REFRESH_TOKEN", "").strip()
        if not api_key or not refresh_token:
            raise BundledNotesError(
                "not_configured",
                "Set BUNDLED_FIREBASE_API_KEY and BUNDLED_FIREBASE_REFRESH_TOKEN.",
            )
        return cls(
            api_key=api_key,
            refresh_token=refresh_token,
            project_id=os.getenv("BUNDLED_FIREBASE_PROJECT_ID", DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID,
            storage_bucket=os.getenv("BUNDLED_FIREBASE_STORAGE_BUCKET", DEFAULT_STORAGE_BUCKET).strip()
            or DEFAULT_STORAGE_BUCKET,
            expected_uid=os.getenv("BUNDLED_FIREBASE_UID", "").strip() or None,
            timeout_seconds=float(os.getenv("BUNDLED_HTTP_TIMEOUT_SECONDS", "30")),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.refresh_token)
