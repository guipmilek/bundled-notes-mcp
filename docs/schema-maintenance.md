# Schema maintenance playbook

Bundled Notes does not publish a versioned API. This project therefore treats the
web application, authenticated Firestore read-backs, and isolated UI workflows as
the compatibility source until an official API/MCP exists.

## Fast drift check

`bundled_schema_status` samples authenticated documents and returns only field
names and value types. It never returns note titles, bodies, filenames, IDs, or
other document values.

```powershell
uv run python scripts/schema_audit.py --sample-size 5
```

Exit code `2` means breaking drift: a required field disappeared or a known field
changed type. New fields are reported as `additive_drift` and remain compatible,
because partial updates preserve unknown data. Use `--fail-on additive` when
refreshing the baseline after a known web release.

The weekly GitHub workflow runs the same read-only check when
`BUNDLED_FIREBASE_API_KEY` and `BUNDLED_FIREBASE_REFRESH_TOKEN` repository secrets
are configured. `BUNDLED_FIREBASE_UID` is recommended as an account assertion.

## When the web app changes

1. Read the public Bundled Notes changelog and run the read-only schema audit.
2. Create a unique `RUN_ID` and use only records prefixed with
   `[MCP TEST <RUN_ID>]` for behavior probes.
3. Exercise the changed feature in `https://bundlednotes.app` and compare the
   affected Firestore document immediately before and after the action. Record
   field names, types, paths, enums, and behavior only.
4. Inspect public production JavaScript only to confirm paths, enums, defaults,
   Firebase configuration, or request formats. Do not copy minified application
   code into this repository.
5. Update the smallest compatibility seam:
   - field/type expectations: `src/bundled_notes_mcp/schema.py`;
   - enums and input validation: `src/bundled_notes_mcp/models.py`;
   - paths, defaults, and read/write behavior: `src/bundled_notes_mcp/client.py`;
   - Firebase wire formats: `firestore.py` or `storage.py`;
   - hosted/remote compatibility wrappers: `overrides.py`;
   - public MCP contract: `tools.py` only when the user-facing capability changes.
6. Add a regression fixture for the old and new shapes. Legacy documents must
   continue to work when the web app can still produce or retain them.
7. Run the local gates and then `scripts/live_integration.py` against disposable
   records. Verify UI interoperability where practical.
8. Remove every tracked bundle, entry, tag, template, catalog record, and Storage
   object. Run `scripts/cleanup_test_artifacts.py` for the exact `RUN_ID` if an
   interrupted probe leaves residue.

Never read browser cookies/local storage, commit API responses, or store session
exports in the repository. `rollout-*.jsonl` and generated schema reports are
ignored because historical sessions can contain credentials or private content.

## Drift classification

| Signal | Meaning | Typical action |
| --- | --- | --- |
| `compatible` | Observed fields match the contract | No change |
| `additive_drift` | Bundled Notes added fields | Document, add tests, preserve by partial patch |
| `breaking_drift` | Required field missing or type changed | Reproduce in UI, add adapter, release promptly |
| Schema compatible but live test fails | Enum/default/rule/behavior changed | Compare UI before/after and update domain logic |
| Authentication/status fails | Firebase config, rules, or token flow changed | Re-run bootstrap discovery and inspect public config |

## Official API migration

Keep MCP tool names and output shapes stable when possible. When Bundled Notes
publishes an official API or MCP, implement it behind `BundledNotesClient`, run the
same contract and integration suite against both backends, then retire Firebase
access only after parity and rollback are proven.


## Maintenance cadence and pull requests

The scheduled read-only audit is the early-warning mechanism, not an automatic
production migration. When the fingerprint or Bundled Notes behavior changes,
prepare a scoped branch and pull request with the sanitized drift summary,
compatibility decision, focused tests, documentation updates, and disposable live
audit results. Publish through the approved GitHub connector workflow and do not
merge until the repository owner explicitly approves it.

