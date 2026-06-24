# Roadmap

## Phase 0: Project control files

- Create private repository.
- Add README, `.gitignore`, AGENTS, specification, test plan and roadmap.
- Establish safety rules and development strategy.

## Phase 1: Skeleton project

- Add Python package structure.
- Add development tooling.
- Add empty module boundaries.
- Add initial synthetic fixtures.
- Add first cloud CI workflow.

## Phase 2: Metadata and folder tree

- Parse local copies of RM2 metadata files.
- Identify folders, documents and trash/deleted items.
- Reconstruct visible folder tree.
- Generate planned PDF output paths.
- Add duplicate-name and path-safety handling.

## Phase 3: Raw backup acquisition

- Add read-only SSH/rsync raw sync from RM2 to RPI.
- Copy xochitl and templates into `raw/current`.
- Add pre-flight checks.
- Add dry-run behaviour.
- Add run summaries.

## Phase 4: Manifest and change detection

- Add persistent run state.
- Track documents, source changes and previous render status.
- Queue only changed or failed documents for rendering.
- Record failures and warnings.

## Phase 5: First local renderer integration

- Add modular renderer interface.
- Add first v6-aware local renderer backend.
- Render one simple notebook page.
- Render one complete multi-page notebook.
- Validate output PDFs.

## Phase 6: PDF mirror publication

- Compose multi-page PDFs.
- Publish validated PDFs atomically into `pdf/current`.
- Preserve previous successful PDFs on failure.
- Add conservative handling of moved, renamed, deleted and trashed items.

## Phase 7: Spare RM2 hardware-in-the-loop testing

- Configure RPI self-hosted GitHub runner.
- Use spare RM2 `Backup Test/` folder as a stable hardware fixture.
- Test raw sync, metadata parsing, rendering and validation on real data.
- Keep production RM2 isolated.

## Phase 8: systemd service and timer

- Add install documentation.
- Add systemd service/timer templates.
- Add status and log inspection guidance.
- Add rollback guidance.

## Phase 9: Production deployment

- Deploy to RPI against production RM2 in read-only mode.
- Keep spare RM2 as regression test device.
- Add periodic health reports.
- Add release tagging and rollback policy.

## Future enhancements

- Add additional renderer backends.
- Add PDF visual comparison tools.
- Add local dashboard.
- Add automatic GitHub issue creation from failed hardware tests.
- Add Codex-assisted bug-fix loop from CI failures.
- Add retention policy for raw and PDF snapshots.
