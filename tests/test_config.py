from __future__ import annotations

from bundled_notes_mcp.config import Settings


def test_environment_configuration(monkeypatch) -> None:
    monkeypatch.setenv("BUNDLED_FIREBASE_API_KEY", "public")
    monkeypatch.setenv("BUNDLED_FIREBASE_REFRESH_TOKEN", "secret")
    monkeypatch.setenv("BUNDLED_FIREBASE_PROJECT_ID", "project")
    monkeypatch.setenv("BUNDLED_FIREBASE_STORAGE_BUCKET", "bucket")
    monkeypatch.setenv("BUNDLED_FIREBASE_UID", "uid")
    settings = Settings.from_env()
    assert settings.api_key == "public"
    assert settings.refresh_token == "secret"
    assert settings.project_id == "project"
    assert settings.storage_bucket == "bucket"
    assert settings.expected_uid == "uid"
