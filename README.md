# rm2-pdf-backup

Automated Raspberry Pi backup and PDF export workflow for reMarkable 2 notebooks.

This project is intended to build a safe, one-way backup pipeline from a reMarkable 2 tablet to Raspberry Pi storage. The final system should:

- copy the raw reMarkable `xochitl` document store over SSH;
- preserve a raw backup for recovery;
- reconstruct the visible reMarkable folder structure from metadata;
- render notebooks and annotated documents to multi-page PDFs on the Raspberry Pi;
- publish a human-readable PDF mirror;
- validate every generated PDF before replacing a previous successful export;
- run automatically using a controlled service/timer;
- support iterative development using GitHub, CI, a spare RM2 test device, and Codex-assisted pull requests.

## Non-negotiable safety rules

- The workflow must be one-way: RM2 to Raspberry Pi only.
- The application must never write to, delete from, or modify the RM2.
- Raw backup is mandatory and must happen before PDF rendering.
- Failed PDF rendering must not replace a previous good PDF.
- Real RM2 data, generated PDFs, logs, SQLite databases, SSH keys, and local configuration must not be committed to this repository.

## Planned architecture

```text
RM2 over SSH
  -> raw xochitl/templates backup on Raspberry Pi
  -> metadata indexer
  -> visible folder-tree reconstruction
  -> change detector and render queue
  -> local renderer backends
  -> PDF composer and validator
  -> atomic PDF mirror publication
  -> manifest/database, logs and reports
```

## Development approach

This repository will be developed as a Python project with modular components, tests, GitHub Actions for normal CI, and a Raspberry Pi self-hosted runner for hardware-in-the-loop testing against a spare RM2.

The detailed behaviour contract is in `SPEC.md`. Codex/project-agent instructions are in `AGENTS.md`. The validation strategy is in `TEST_PLAN.md`.
