# RPI selected-notebook rerender workflow

Use the `RPI rerender selected RM2 notebooks` workflow to rerender specific notebooks on the Raspberry Pi self-hosted runner.

This workflow is for targeted renderer validation after fixes such as issue #56 and issue #58. It should be run against the spare/test RM2 profile, not the production or beamline RM2.

## What it does

The workflow:

1. runs only on the RPI self-hosted runner labels `self-hosted`, `rpi`, `rm2`, and `dev`;
2. installs the package with the `dev` and `rmc` extras;
3. optionally refreshes the raw backup from the spare RM2 when `source_mode=rm2-live`;
4. builds a temporary raw subset containing only the selected notebook UUIDs and required parent metadata;
5. copies template assets into the temporary subset when they are present;
6. runs the normal `run_local` render, validate, and publish pipeline against that subset;
7. uploads the temporary PDFs, staging outputs, run report, and summary as workflow artifacts.

## Default notebooks

The workflow defaults to the notebooks that previously exposed renderer/template problems:

```text
Notebook 3
uuid: 285738be-c346-4923-ac26-70d7ff02e5f5
previous issue: malformed_svg / usable=0/1
```

```text
Folder2/Notebook 2
uuid: 05d1a569-8d05-4f6e-9e99-6a5bff2afc16
previous issue: template_refs=mind_map_rm2 / template_missing=mind_map_rm2
```

## Inputs

- `notebook_uuids`: comma-separated notebook UUIDs to rerender.
- `notebook_names`: optional comma-separated names for the uploaded summary.
- `source_mode`:
  - `raw-backup`: use the existing local raw backup under the configured `raw_current` path;
  - `rm2-live`: run the existing read-only raw sync first, then rerender from the refreshed local copy.
- `config_path`: private Raspberry Pi config file, normally `/etc/rm2-backup-test/config.toml`.
- `publish_current`:
  - `false`: write PDFs only to workflow artifacts;
  - `true`: publish to the configured `pdf_current` path, but only after validation passes.

## Safety notes

- The workflow does not write to the RM2.
- `source_mode=rm2-live` uses the existing read-only `run_raw_sync` implementation.
- `publish_current=false` is the default and should be used for normal validation.
- `publish_current=true` should only be used after reviewing artifact output from a previous run.
- Runtime data and generated PDFs are uploaded as artifacts, not committed to the repository.
