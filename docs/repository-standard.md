# Repository Standard

This repository follows the same maintainability baseline as
[`guipmilek/despezzas-mcp`](https://github.com/guipmilek/despezzas-mcp) while
keeping Bundled Notes-specific architecture and safety rules explicit.

## Shared baseline

- Python package under `src/`, tests under `tests/`, operational helpers under
  `scripts/`, and maintainer guidance under `docs/`.
- Portuguese `README.md` plus English `README.en.md`.
- `AGENTS.md`, `llms.txt`, `PROJECT_PATHS.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  and `WRITES.md` at repository root.
- CI gates for formatting, linting, tests, and FastMCP catalog inspection.
- Issue and pull-request templates with privacy and confirmation checks.
- Dedicated architecture map, agent playbook, task template, deployment guide,
  and MCP client setup guide.

## Project-specific extensions

Bundled Notes additionally maintains a sanitized schema contract, weekly read-only
schema audit, Firebase data-model notes, reverse-engineering boundaries, attachment
lifecycle tests, and disposable live-integration cleanup tooling. These extensions
are intentional and must not be removed merely to make both repositories identical.

## Consistency rule

Repository alignment means equivalent purpose, navigation, safety, and validation;
it does not mean copying product-specific files or stale absolute paths. When a
shared convention changes in either repository, review whether the other project
needs the same class of update and document deliberate differences.

Before merge, verify:

1. Both READMEs describe the same capabilities, limits, commands, and deployment.
2. `llms.txt` exactly matches the runtime tool catalog.
3. Every relative Markdown link resolves to a tracked file or local heading.
4. Agent instructions and PR checks match CI.
5. No examples contain real credentials, account data, or machine-specific paths.
