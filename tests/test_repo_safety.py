from __future__ import annotations

import re
from pathlib import Path

from tests.test_tools import EXPECTED_TOOLS

ROOT = Path(__file__).parents[1]


def test_documented_tool_catalog_matches_runtime_contract() -> None:
    documented = set(re.findall(r"^- `(bundled_[a-z_]+)`$", (ROOT / "llms.txt").read_text(encoding="utf-8"), re.M))
    assert documented == EXPECTED_TOOLS


def test_env_example_contains_no_assigned_credentials() -> None:
    values = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    assert values["BUNDLED_FIREBASE_API_KEY"] == ""
    assert values["BUNDLED_FIREBASE_REFRESH_TOKEN"] == ""
    assert values["BUNDLED_FIREBASE_UID"] == ""


def test_open_source_community_files_exist() -> None:
    required = {
        ".github/workflows/ci.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "README.en.md",
        "README.md",
        "SECURITY.md",
        "WRITES.md",
    }
    assert all((ROOT / relative).is_file() for relative in required)


def test_sensitive_session_exports_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "rollout-*.jsonl" in ignored
    assert "schema-report*.json" in ignored
