# Agent Task Template

```text
Task:
<specific desired change>

Preflight:
- Confirm repository, branch, and git status.
- Read AGENTS.md, llms.txt, docs/agent-playbook.md, and the relevant domain docs.
- Run the sanitized schema audit before adapting to a Bundled Notes release.

Rules:
- Keep confirm:true on every write.
- Preserve unknown Firestore fields and re-read confirmed writes.
- Never commit secrets, sessions, rollout exports, API responses, notes, or attachments.
- Use only [MCP TEST <RUN_ID>] records for live tests and remove every artifact.
- Keep Horizon authentication enabled and payload logging disabled.
- Keep public MCP names/output shapes stable where possible.

Checklist:
- [ ] Implement the smallest scoped change
- [ ] Add focused positive and negative tests
- [ ] Run Ruff, pytest, fastmcp inspect, and build
- [ ] Update README.md, README.en.md, llms.txt, WRITES.md, and relevant docs
- [ ] Verify catalog count and schema compatibility
- [ ] Run an authorized disposable live audit when required
- [ ] Prove baseline restoration and zero residue
- [ ] Review the diff for sensitive or unrelated files
- [ ] Open a PR; do not merge without owner approval
```
