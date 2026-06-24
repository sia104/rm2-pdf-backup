# Raspberry Pi installation notes

These notes cover repository-side deployment preparation up to the point where a human operator runs commands on the Raspberry Pi. Start with local dry-runs and the placeholder renderer before enabling device access.

## 1. Install locally on the Raspberry Pi

Create a Python virtual environment, install the package, and verify the console script works.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
```

Expected result: the command prints planned relative PDF paths for the synthetic fixture set.

## 2. Create local storage areas

The intended runtime layout is:

```text
raw/current/xochitl
raw/current/templates
pdf/current
db
logs
reports
staging
```

Keep raw backup data separate from the PDF mirror. The raw area is the recovery source of truth; the PDF area is a derived export.

## 3. Prepare configuration

Use a local config file based on the configuration model in `src/rm2_backup/config.py`. At minimum, it needs:

```toml
[rm2]
host = "SPARE_RM2_HOST_OR_IP"
user = "root"
port = 22

[paths]
backup_root = "backup"
raw_current = "backup/raw/current"
pdf_current = "backup/pdf/current"
staging = "backup/staging"
database = "backup/db/rm2-backup.sqlite"
reports = "backup/reports"
logs = "backup/logs"

[renderer]
mode = "placeholder"
```

Use the spare RM2 first. Do not put private SSH keys or real production host details in the repository.

## 4. Inspect the raw-sync plan

Before executing any sync, inspect the planned commands:

```bash
rm2-backup sync-plan --config config.toml
```

This should show two pull-style rsync commands: one for `xochitl` and one for templates. The project design is pull-only from the device into local storage.

## 5. Run local pipeline against copied raw data

Once raw data already exists locally, run:

```bash
rm2-backup run-local --config config.toml
```

With the placeholder renderer, this validates the orchestration path: local raw metadata, tree reconstruction, render plan, placeholder PDF creation, validation, manifest update, and publication into the configured PDF mirror.

## 6. Systemd examples

Example unit files are in `packaging/systemd/`. They are templates and must be reviewed on the Raspberry Pi before use.

Recommended checks before enabling a timer:

```bash
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
rm2-backup sync-plan --config config.toml
rm2-backup run-local --config config.toml
```

Only enable the timer after a manual run is successful on the spare RM2.

## Safety rules

- Use the spare RM2 first.
- Keep raw data and generated PDFs out of git.
- Do not commit credentials, SSH keys, host-specific config, logs, databases, or real RM2 files.
- Treat raw backup as the recovery source of truth.
- Do not replace good PDFs with failed renders.
