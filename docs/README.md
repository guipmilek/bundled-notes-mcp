# Documentation

This directory is the maintainer source of truth for architecture, safe operation,
testing, deployment, and upstream compatibility.

| Document | Purpose |
| --- | --- |
| [Agent architecture map](agent-architecture-map.md) | Runtime flow, ownership, and change routing |
| [Agent playbook](agent-playbook.md) | Preflight, invariants, verification, and handoff |
| [Agent task template](agent-task-template.md) | Reusable prompt/checklist for scoped changes |
| [ChatGPT app setup](chatgpt-app-setup.md) | Connect the hosted MCP to an MCP client |
| [Deployment](deployment.md) | Prefect Horizon configuration and release checks |
| [Schema maintenance](schema-maintenance.md) | Detect and adapt to Bundled Notes changes |
| [Testing](testing.md) | Unit, catalog, schema, and live integration strategy |
| [Data model](data-model.md) | Observed Firebase collections and fields |
| [Reverse engineering](reverse-engineering.md) | Evidence boundaries and compatibility posture |
| [Repository standard](repository-standard.md) | Shared conventions with `despezzas-mcp` |

User-facing setup and capability summaries remain in `README.md` and
`README.en.md`. Mutation semantics remain in `WRITES.md`; security disclosure and
credential rules remain in `SECURITY.md`.
