# Agent instructions for rm2-pdf-backup

These instructions apply to all automated coding agents working in this repository, including Codex.

## Project purpose

Build a safe, one-way Raspberry Pi service that backs up a reMarkable 2 over SSH, reconstructs the visible folder structure, renders notebooks/documents to multi-page PDFs locally on the Raspberry Pi, and publishes a validated PDF mirror.

## Hard safety rules

1. Never write to the RM2.
2. Never delete or modify files on the RM2.
3. Never require reMarkable cloud access.
4. Never commit real RM2 data, generated PDFs, logs, databases, SSH keys, IP-specific configuration, or secrets.
5. Never replace a previous successful PDF export with a failed or unvalidated output.
6. Raw backup must be treated as the recovery source of truth.
7. A failed document render must not abort the entire backup run unless the failure is systemic and unsafe.
8. Prefer conservative behaviour over data loss or silent corruption.

## Implementation preferences

- Use Python for the main application logic.
- Use Bash only for small system integration wrappers where appropriate.
- Use `rsync` over SSH for raw copy from the RM2.
- Use SQLite for persistent manifest/run state once change tracking is implemented.
- Keep renderers modular. Do not hard-wire the whole project to a single renderer.
- Treat local rendering as potentially imperfect and always validate output.
- Use atomic publication: render into staging, validate, then move into the current PDF mirror.
- Keep production RM2 and spare/test RM2 workflows separate.

## Expected repository structure

The intended structure is:

```text
src/rm2_backup/
  config.py
  raw_sync.py
  metadata.py
  tree.py
  manifest.py
  render_queue.py
  renderers/
  pdf_compose.py
  validate.py
  publish.py
  report.py

tests/
fixtures/
docs/
```

Do not create large binary fixtures in the repository. Small synthetic text fixtures are acceptable. Real raw RM2 data must stay outside the repository.

## Testing expectations

For every feature, add or update tests. Prefer small, deterministic tests using synthetic fixtures. Hardware-in-the-loop tests against the spare RM2 should be isolated from normal cloud CI and should never run on untrusted external pull requests.

## Pull request expectations

Each PR should include:

- a clear summary;
- the risk level;
- tests added or updated;
- any manual validation steps;
- whether it touches RM2 access, filesystem writes, rendering, or deletion/archive behaviour.

## When uncertain

If a behaviour could cause data loss, modify the RM2, leak private notebook data, or silently generate misleading PDFs, stop and ask for clarification rather than guessing.
