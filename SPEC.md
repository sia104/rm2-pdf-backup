# rm2-pdf-backup specification

## 1. Goal

Create a safe, automated, one-way backup workflow for a reMarkable 2 connected to a Raspberry Pi over a private network. The backup must preserve raw RM2 data and create a human-readable PDF mirror that recreates the visible RM2 folder structure.

## 2. Source device

The RM2 is treated as a read-only SSH source. The application must copy data from the tablet but must not modify the tablet.

Expected source areas:

```text
/home/root/.local/share/remarkable/xochitl/
/usr/share/remarkable/templates/
```

Optional source areas may be added later for custom templates or configuration, but secrets must not be committed.

## 3. Backup outputs

The Raspberry Pi should maintain these conceptual areas:

```text
raw/current/        latest raw local copy
raw/snapshots/      optional dated raw snapshots
pdf/current/        latest validated PDF mirror
pdf/snapshots/      optional dated PDF snapshots
staging/            temporary render/publish area
db/                 manifest and run state
logs/               local run logs
```

## 4. Folder reconstruction

The RM2 visible folder tree must be reconstructed from local copies of metadata files, not by assuming the raw filesystem already matches the visible tree.

The metadata parser must extract at least:

- UUID;
- `visibleName`;
- `type`;
- `parent`;
- deleted/trash state;
- last modified metadata if available.

The tree builder must resolve parent-child relationships and produce stable output paths.

## 5. Document types

The system should eventually support:

- native handwritten notebooks;
- notebooks using templates;
- multi-page notebooks;
- annotated PDFs;
- EPUB-derived documents where the RM2 stores an internal converted PDF;
- documents with layers, highlighter, eraser, and typed text where renderer support permits.

Unsupported features must be reported clearly rather than silently ignored.

## 6. PDF output rules

Each visible RM2 notebook/document should produce one multi-page PDF. The output path should match the visible RM2 folder structure.

Example:

```text
RM2 visible path:
  Work/DIAD/Beamline notes

PDF mirror path:
  pdf/current/Work/DIAD/Beamline notes.pdf
```

Name collisions must be handled safely. The preferred behaviour is to preserve the visible name where unique and add a short disambiguator only when needed.

## 7. Change detection

A document should be considered for re-rendering if any relevant input changes, including:

- metadata;
- content/page list;
- page stroke files;
- original PDF/EPUB-derived PDF;
- template assets;
- renderer version;
- previous render status.

The system should not re-render unchanged documents unnecessarily.

## 8. Rendering

Rendering should be implemented behind a modular renderer interface. The first production renderer is expected to target modern reMarkable software 3.x/v6 data. Additional renderers may be added as fallbacks.

Rendering must happen on the Raspberry Pi from the local raw copy, not on the RM2.

## 9. Validation

Before publishing, every generated PDF must be validated. Minimum validation:

- file exists;
- file size is greater than zero;
- file is parseable as a PDF;
- page count is greater than zero;
- expected page count matches where the expected value is reliable.

A failed validation must not replace a previous successful PDF.

## 10. Publishing

PDFs must be rendered into staging first. Only validated outputs may be atomically published into `pdf/current`.

Deletion behaviour must be conservative. Deleted or trashed RM2 items must not cause immediate destructive deletion from the backup mirror unless an explicit archive/retention policy is implemented and tested.

## 11. Manifest and reporting

The system should maintain persistent run state, initially as simple metadata and eventually in SQLite. It should record:

- backup runs;
- documents seen;
- render decisions;
- successful PDF exports;
- failed exports;
- warnings;
- renderer used and renderer version;
- hashes or other change-detection state.

Every run should produce a human-readable summary.

## 12. Automation

The final service should run under systemd on the Raspberry Pi. Scheduling should use a systemd timer. Normal CI should run in GitHub Actions. Hardware tests should run on a Raspberry Pi self-hosted runner connected only to the spare RM2.

## 13. Security and privacy

The repository must not contain real notebooks, raw RM2 data, generated PDFs, logs with document names from production devices, SSH keys, IP-specific secrets, or cloud credentials.
