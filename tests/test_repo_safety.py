from __future__ import annotations

import re
import struct
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


def test_open_source_and_maintainer_files_exist() -> None:
    required = {
        ".github/workflows/ci.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        "AGENTS.md",
        "assets/bundled-notes-mcp.png",
        "CONTRIBUTING.md",
        "LICENSE",
        "PROJECT_PATHS.md",
        "README.en.md",
        "README.md",
        "SECURITY.md",
        "WRITES.md",
        "docs/README.md",
        "docs/agent-architecture-map.md",
        "docs/agent-playbook.md",
        "docs/agent-task-template.md",
        "docs/chatgpt-app-setup.md",
        "docs/deployment.md",
        "docs/repository-standard.md",
    }
    assert all((ROOT / relative).is_file() for relative in required)


def test_relative_markdown_links_resolve() -> None:
    markdown_files = [*ROOT.glob("*.md"), *ROOT.joinpath("docs").glob("*.md")]
    broken: list[tuple[str, str]] = []
    for document in markdown_files:
        content = document.read_text(encoding="utf-8")
        for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", content):
            path = target.split("#", 1)[0]
            if not path or "://" in path or path.startswith("mailto:"):
                continue
            if not (document.parent / path).resolve().is_file():
                broken.append((document.relative_to(ROOT).as_posix(), target))
    assert broken == []


def test_readmes_share_release_contract() -> None:
    readmes = [(ROOT / name).read_text(encoding="utf-8") for name in ("README.md", "README.en.md")]
    required_markers = {
        "43",
        "bundled_schema_status",
        "src/bundled_notes_mcp/server.py:mcp",
        "https://seu-servidor.fastmcp.app/mcp",
    }
    for readme in readmes:
        assert all(marker in readme for marker in required_markers)


def test_sensitive_session_exports_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "rollout-*.jsonl" in ignored
    assert "schema-report*.json" in ignored


def test_chatgpt_connector_icon_contract() -> None:
    icon = ROOT / "assets/bundled-notes-mcp.png"
    data = icon.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) <= 100 * 1024
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (512, 512)


def test_public_docs_never_advertise_the_maintainer_deployment() -> None:
    public_docs = [
        ROOT / "README.md",
        ROOT / "README.en.md",
        ROOT / "docs/chatgpt-app-setup.md",
        ROOT / "docs/deployment.md",
        ROOT / "SECURITY.md",
        ROOT / "llms.txt",
        ROOT / "AGENTS.md",
        ROOT / "PROJECT_PATHS.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in public_docs)
    assert "https://bundled-notes-mcp.fastmcp.app/mcp" not in combined
    assert "Um fork e um deployment por conta" in combined
    assert "one deployment per account" in combined
