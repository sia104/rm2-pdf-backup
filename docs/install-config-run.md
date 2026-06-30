# Installation, configuration, and running

This guide is the operator entry point for installing `rm2-pdf-backup`, preparing configuration, and running the workflow safely.

The project is designed as a one-way backup pipeline:

```text
RM2 -> Raspberry Pi raw backup -> local render/validate -> PDF mirror
```

The RM2 is always treated as a read-only source. Rendering and publication happen from the Raspberry Pi's local raw copy, not on the RM2.

## Safety boundary

Follow these rules before running anything against hardware:

- Use a non-production validation RM2 first.
- Do not use the beamline or production RM2 until the production checklist passes.
- Do not run SSH, SCP, or rsync to the RM2 from a developer Mac.
- Do not write to, delete from, or modify the RM2.
- Do not commit real RM2 data, generated PDFs, logs, SQLite databases, SSH keys, IP addresses, host-specific configuration, or secrets.
- Do not enable a systemd timer until the matching manual service command has completed successfully.
- Stop if any command plan contains destructive behaviour such as `--delete`.

## Requirements

Raspberry Pi operation requires:

- Python 3.11 or newer;
- `pip`;
- `git`;
- a checked-out copy of this repository on the Raspberry Pi;
- renderer dependencies from `.[rmc]` when using `mode = "rmc-svg"`;
- network reachability from the Raspberry Pi to the validation or production RM2;
- RM2 SSH access configured on the Raspberry Pi, not in this repository;
- enough local storage for `raw`, `pdf`, `staging`, `db`, `reports`, and `logs`;
- a reviewed path for pre-production validation before production timer enablement.

Do not store private SSH key paths, passwords, tokens, real hostnames, or real IP addresses in committed files.

## Install on the Raspberry Pi

On the Raspberry Pi, check out the repository and install it into a virtual environment.

```bash
sudo mkdir -p /opt/rm2-pdf-backup
sudo chown "$USER":"$USER" /opt/rm2-pdf-backup
cd /opt
git clone https://github.com/sia104/rm2-pdf-backup.git rm2-pdf-backup
cd /opt/rm2-pdf-backup
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[rmc]"
rm2-backup --help
```

Keep the Git checkout, virtual environment, and runtime backup data in separate places. Use `pip install -e ".[rmc]"` for runtime use. Additional internal validation notes are documented separately under `docs/development/`.

## Create runtime folders

Create the runtime folders on the Raspberry Pi before running the pipeline. These folders must not be inside the Git repository.

For pre-production validation:

```bash
sudo mkdir -p /srv/rm2-backup-validation/raw/current
sudo mkdir -p /srv/rm2-backup-validation/pdf/current
sudo mkdir -p /srv/rm2-backup-validation/staging
sudo mkdir -p /srv/rm2-backup-validation/db
sudo mkdir -p /srv/rm2-backup-validation/reports
sudo mkdir -p /srv/rm2-backup-validation/logs
sudo chown -R "$USER":"$USER" /srv/rm2-backup-validation
```

For production:

```bash
sudo mkdir -p /srv/rm2-backup/raw/current
sudo mkdir -p /srv/rm2-backup/pdf/current
sudo mkdir -p /srv/rm2-backup/staging
sudo mkdir -p /srv/rm2-backup/db
sudo mkdir -p /srv/rm2-backup/reports
sudo mkdir -p /srv/rm2-backup/logs
sudo chown -R "$USER":"$USER" /srv/rm2-backup
```

The `raw/current` directory receives the local RM2 copy. The `pdf/current` directory receives only validated published PDFs. The `staging` directory is temporary and should not be used as the final mirror.

## Runtime storage layout

The application expects separate areas for raw source data, generated PDFs, staging, state, reports, and logs.

Conceptual layout:

```text
raw/current/        latest local raw copy
raw/snapshots/      optional dated raw snapshots
pdf/current/        latest validated PDF mirror
pdf/snapshots/      optional dated PDF snapshots
staging/            temporary render/publish area
db/                 manifest and run state
reports/            human-readable run reports
logs/               local service logs
```

The raw area is the recovery source of truth. The PDF mirror is a derived convenience output.

## Configuration files

The application config is TOML with three tables:

- `[rm2]` for read-only source connection details;
- `[paths]` for local Raspberry Pi storage locations;
- `[renderer]` for renderer selection.

Example files:

- `docs/app-config-example.toml` is a small application example using placeholder values.
- `deploy/config/production.example.toml` is a production template with placeholders only.
- `docs/rpi-ssh-access.md` explains passwordless SSH alias setup for unattended Raspberry Pi runs.

Copy examples to private local files before editing:

```bash
cp deploy/config/production.example.toml config.local.toml
```

For pre-production validation on the Raspberry Pi, copy the production template to a private validation config, then edit only the private copy:

```bash
sudo mkdir -p /etc/rm2-backup-validation
sudo cp deploy/config/production.example.toml /etc/rm2-backup-validation/config.toml
sudoedit /etc/rm2-backup-validation/config.toml
```

Use the validation RM2 connection value in `/etc/rm2-backup-validation/config.toml`, not the production RM2. Keep the `/srv/rm2-backup-validation` paths so the validation run is clearly separate from production.

For production preparation on the Raspberry Pi only:

```bash
sudo mkdir -p /etc/rm2-backup
sudo cp deploy/config/production.example.toml /etc/rm2-backup/config.toml
sudoedit /etc/rm2-backup/config.toml
```

Do not commit edited local or production config files.

## Configuration reference

`[rm2]`:

```toml
[rm2]
host = "VALIDATION_RM2_HOST_OR_ALIAS"
user = "root"
port = 22
```

`host` is resolved on the Raspberry Pi. Use a private local DNS name, hosts entry, SSH alias, or local-only value. For validation, this should identify the validation RM2. Do not commit a real production host or IP address.

For SSH alias mode, prefer:

```toml
[rm2]
host = "rm2"
ssh_alias = true
```

This makes raw sync use `rm2:/path` so the Raspberry Pi user's private `~/.ssh/config` controls the real host, user, port, and identity file. See `docs/rpi-ssh-access.md`.

`user` should normally be `root` for RM2 SSH access.

`port` should normally be `22`.

`ssh_key` is optional in the parser. If you use it, put it only in the private Raspberry Pi config:

```toml
[rm2]
host = "VALIDATION_RM2_HOST_OR_ALIAS"
user = "root"
port = 22
ssh_key = "/PRIVATE/RPI/ONLY/PATH/TO/RM2_KEY"
```

Do not commit the edited config, the key path, or the key.

Do not set `user = ""`; empty user values are invalid. Use `ssh_alias = true` for alias-based access.

`[paths]`:

```toml
[paths]
backup_root = "/srv/rm2-backup-validation"
raw_current = "/srv/rm2-backup-validation/raw/current"
pdf_current = "/srv/rm2-backup-validation/pdf/current"
staging = "/srv/rm2-backup-validation/staging"
database = "/srv/rm2-backup-validation/db/rm2-backup.sqlite"
reports = "/srv/rm2-backup-validation/reports"
logs = "/srv/rm2-backup-validation/logs"
```

Keep `raw_current` and `pdf_current` separate. Do not put runtime output inside a path that will be committed.

For production:

```toml
[paths]
backup_root = "/srv/rm2-backup"
raw_current = "/srv/rm2-backup/raw/current"
pdf_current = "/srv/rm2-backup/pdf/current"
staging = "/srv/rm2-backup/staging"
database = "/srv/rm2-backup/db/rm2-backup.sqlite"
reports = "/srv/rm2-backup/reports"
logs = "/srv/rm2-backup/logs"
```

Use a separate validation root and production root. Do not point validation runs at the production runtime path.

`[renderer]`:

```toml
[renderer]
mode = "rmc-svg"
include_templates = true
```

Supported modes are:

- `external`: call a configured external renderer command;
- `rmc-svg`: render RM pages through the repository's RM/SVG composition path.
- `placeholder`: orchestration-only mode kept for development use.

Template composition currently requires `mode = "rmc-svg"`.

`rmc-svg` requires an `rmc` executable on the Raspberry Pi `PATH`. Before using
this renderer on the Raspberry Pi, verify:

```bash
command -v rmc
rmc --help
```

If `rm2-backup run-local` reports `category=renderer_executable_not_found`,
install the renderer extra and rerun the local pipeline:

```bash
cd /opt/rm2-pdf-backup
. .venv/bin/activate
pip install -e ".[rmc]"
```

The backup raw copy should be left intact while fixing renderer installation.

Use `placeholder` only for contributor-side orchestration checks.

## Inspect the raw sync plan

Before running any raw copy, inspect the planned commands on the Raspberry Pi:

```bash
rm2-backup sync-plan --config /etc/rm2-backup-validation/config.toml
```

The output must be pull-only from the RM2 to Raspberry Pi storage. It must not include `--delete`.

## Run the local pipeline

After raw data already exists on the Raspberry Pi, run:

```bash
rm2-backup run-local --config /etc/rm2-backup-validation/config.toml
```

This uses local raw metadata and files to:

- reconstruct the visible RM2 folder tree;
- plan PDF outputs;
- render supported documents;
- validate generated PDFs;
- publish only validated outputs;
- update manifest/report state;
- print a summary including the report path.

A failed document render should be reported without replacing a previous successful PDF and without aborting unrelated documents unless the failure is systemic and unsafe.

## Pre-production validation

Use this sequence before enabling any production timer:

1. Install the repository under `/opt/rm2-pdf-backup`.
2. Create runtime folders under `/srv/rm2-backup-validation`.
3. Copy `deploy/config/production.example.toml` to `/etc/rm2-backup-validation/config.toml`.
4. Edit `/etc/rm2-backup-validation/config.toml` so `[rm2].host` points to the validation RM2 and all `[paths]` values point under `/srv/rm2-backup-validation`.
5. Run `rm2-backup sync-plan --config /etc/rm2-backup-validation/config.toml` and verify it is pull-only and has no `--delete`.
6. Run the reviewed raw copy from the Raspberry Pi.
7. Run `rm2-backup run-local --config /etc/rm2-backup-validation/config.toml`.
8. Review the newest report under `/srv/rm2-backup-validation/reports`.
9. Inspect `/srv/rm2-backup-validation/pdf/current` for validated outputs.
10. Repeat the run to confirm unchanged documents are skipped where expected.

## Systemd operation

Systemd files are examples and must be reviewed on the Raspberry Pi before enablement. The production-oriented examples are:

- `packaging/systemd/rm2-backup.service.example`;
- `packaging/systemd/rm2-backup.timer.example`.

Safe order:

1. Complete pre-production validation.
2. Inspect `rm2-backup sync-plan` for the production config.
3. Manually run the production config on the Raspberry Pi.
4. Review the report and published outputs.
5. Enable the production timer only after the manual service run is accepted.

Production timer enablement is gated by `docs/mvp-production-deployment.md`.

## MVP production gate

Do not deploy to the production RM2 just because the installation steps succeeded. Production requires the ordered checklist in `docs/mvp-production-deployment.md`, including pre-production validation, manual production dry-run on the Raspberry Pi, report review, and explicit timer enablement only after acceptance.

## Troubleshooting

If `rm2-backup sync-plan` fails, check the TOML file has `[rm2]`, `[paths]`, and valid renderer settings.

If `rm2-backup run-local` reports failed documents, inspect the generated report before changing timers or production configuration.

If a workflow fails on the self-hosted runner, treat that as a failed gate. Fix the repository through a reviewed pull request before moving to the next deployment step.
