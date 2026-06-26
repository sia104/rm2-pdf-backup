# Installation, configuration, and running

This guide is the operator entry point for installing `rm2-pdf-backup`, preparing configuration, and running the workflow safely.

The project is designed as a one-way backup pipeline:

```text
RM2 -> Raspberry Pi raw backup -> local render/validate -> PDF mirror
```

The RM2 is always treated as a read-only source. Rendering and publication happen from the Raspberry Pi's local raw copy, not on the RM2.

## Safety boundary

Follow these rules before running anything against hardware:

- Use the spare/development RM2 first.
- Do not use the beamline or production RM2 until the MVP production checklist passes.
- Do not run SSH, SCP, or rsync to the RM2 from a developer Mac.
- Do not write to, delete from, or modify the RM2.
- Do not commit real RM2 data, generated PDFs, logs, SQLite databases, SSH keys, IP addresses, host-specific configuration, or secrets.
- Do not enable a systemd timer until the matching manual service command has completed successfully.
- Stop if any command plan contains destructive behaviour such as `--delete`.

## Requirements

Local development requires:

- Python 3.11 or newer;
- `pip`;
- `git`;
- development dependencies from `.[dev]` for tests and linting.

Raspberry Pi operation also requires:

- a checked-out copy of this repository on the Raspberry Pi;
- network reachability from the Raspberry Pi to the spare RM2;
- RM2 SSH access configured on the Raspberry Pi, not in this repository;
- enough local storage for `raw`, `pdf`, `staging`, `db`, `reports`, and `logs`;
- GitHub Actions self-hosted runner labels matching the repository workflows for hardware validation.

Do not store private SSH key paths, passwords, tokens, real hostnames, or real IP addresses in committed files.

## Install for local development

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Confirm the console script works without hardware:

```bash
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
```

The command should print planned PDF output paths for synthetic fixtures.

Run normal local checks:

```bash
ruff check .
pytest
```

## Install on the Raspberry Pi

On the Raspberry Pi, check out the repository and install it into a virtual environment.

For a development checkout under the current user:

```bash
mkdir -p "$HOME/src"
cd "$HOME/src"
git clone https://github.com/sia104/rm2-pdf-backup.git
cd rm2-pdf-backup
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
```

If the repository already exists on the Raspberry Pi, update it instead:

```bash
cd "$HOME/src/rm2-pdf-backup"
git fetch origin
git switch main
git pull --ff-only origin main
```

For a production-like checkout, keep the Git checkout, virtual environment, and runtime backup data in separate places:

```bash
sudo mkdir -p /opt/rm2-pdf-backup
sudo chown "$USER":"$USER" /opt/rm2-pdf-backup
cd /opt
git clone https://github.com/sia104/rm2-pdf-backup.git rm2-pdf-backup
cd /opt/rm2-pdf-backup
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
```

Use `pip install -e ".[dev]"` when you want test/lint tooling on the Raspberry Pi. Use `pip install -e .` for a smaller runtime install.

For a production-style service account, keep the virtual environment and runtime storage outside the repository. The committed systemd examples expect the development checkout and runtime root to be reviewed before use.

## Create runtime folders

Create the runtime folders on the Raspberry Pi before running the pipeline. These folders must not be inside the Git repository.

For development/spare-RM2 testing:

```bash
mkdir -p "$HOME/rm2-backup-dev/raw/current"
mkdir -p "$HOME/rm2-backup-dev/pdf/current"
mkdir -p "$HOME/rm2-backup-dev/staging"
mkdir -p "$HOME/rm2-backup-dev/db"
mkdir -p "$HOME/rm2-backup-dev/reports"
mkdir -p "$HOME/rm2-backup-dev/logs"
```

For a production-like rehearsal that still uses the spare RM2, use `/srv`-style paths with a test suffix so it cannot be confused with real production:

```bash
sudo mkdir -p /srv/rm2-backup-test/raw/current
sudo mkdir -p /srv/rm2-backup-test/pdf/current
sudo mkdir -p /srv/rm2-backup-test/staging
sudo mkdir -p /srv/rm2-backup-test/db
sudo mkdir -p /srv/rm2-backup-test/reports
sudo mkdir -p /srv/rm2-backup-test/logs
sudo chown -R "$USER":"$USER" /srv/rm2-backup-test
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

- `docs/local-config-example.toml` is for local metadata planning only.
- `docs/app-config-example.toml` is a small application example using placeholder values.
- `deploy/config/dev.example.toml` is for the spare/development RM2 profile on the Raspberry Pi.
- `deploy/config/production.example.toml` is a production template with placeholders only.

Copy examples to private local files before editing:

```bash
cp deploy/config/dev.example.toml config.local.toml
```

For a production-like spare-RM2 rehearsal on the Raspberry Pi, copy the production template to a private test config, then edit only the private copy:

```bash
sudo mkdir -p /etc/rm2-backup-test
sudo cp deploy/config/production.example.toml /etc/rm2-backup-test/config.toml
sudoedit /etc/rm2-backup-test/config.toml
```

Use the spare RM2 connection value in `/etc/rm2-backup-test/config.toml`, not the production RM2. Keep the `/srv/rm2-backup-test` paths so the rehearsal is production-shaped but clearly separate from real production.

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
host = "SPARE_RM2_HOST_OR_ALIAS"
user = "root"
port = 22
```

`host` is resolved on the Raspberry Pi. Use a private local DNS name, hosts entry, or local-only value. For a production-like rehearsal, this must still identify the spare/test RM2. Do not commit a real production host or IP address.

`user` should normally be `root` for RM2 SSH access.

`port` should normally be `22`.

`ssh_key` is optional in the parser. If you use it, put it only in the private Raspberry Pi config:

```toml
[rm2]
host = "SPARE_RM2_HOST_OR_ALIAS"
user = "root"
port = 22
ssh_key = "/PRIVATE/RPI/ONLY/PATH/TO/RM2_KEY"
```

Do not commit the edited config, the key path, or the key.

`[paths]`:

```toml
[paths]
backup_root = "/home/k11-user/rm2-backup-dev"
raw_current = "/home/k11-user/rm2-backup-dev/raw/current"
pdf_current = "/home/k11-user/rm2-backup-dev/pdf/current"
staging = "/home/k11-user/rm2-backup-dev/staging"
database = "/home/k11-user/rm2-backup-dev/db/rm2-backup.sqlite"
reports = "/home/k11-user/rm2-backup-dev/reports"
logs = "/home/k11-user/rm2-backup-dev/logs"
```

Keep `raw_current` and `pdf_current` separate. Do not put runtime output inside a path that will be committed.

For a production-like rehearsal with the spare RM2:

```toml
[paths]
backup_root = "/srv/rm2-backup-test"
raw_current = "/srv/rm2-backup-test/raw/current"
pdf_current = "/srv/rm2-backup-test/pdf/current"
staging = "/srv/rm2-backup-test/staging"
database = "/srv/rm2-backup-test/db/rm2-backup.sqlite"
reports = "/srv/rm2-backup-test/reports"
logs = "/srv/rm2-backup-test/logs"
```

Use `/srv/rm2-backup` only for the real production profile after the spare-RM2 gates and MVP production checklist pass.

`[renderer]`:

```toml
[renderer]
mode = "rmc-svg"
include_templates = true
```

Supported modes are:

- `placeholder`: test orchestration without real notebook rendering;
- `external`: call a configured external renderer command;
- `rmc-svg`: render RM pages through the repository's RM/SVG composition path.

Template composition currently requires `mode = "rmc-svg"`.

For production-like testing with the spare RM2, use:

```toml
[renderer]
mode = "rmc-svg"
include_templates = true
```

Use `placeholder` only when testing orchestration without real rendering.

## Local dry-runs without hardware

Plan PDF paths from synthetic metadata:

```bash
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
```

Or use the planning config:

```bash
rm2-backup plan --config docs/local-config-example.toml
```

These commands do not contact an RM2.

## Inspect the raw sync plan

Before running any raw copy, inspect the planned commands on the Raspberry Pi:

```bash
rm2-backup sync-plan --config config.local.toml
```

For the production-like spare-RM2 rehearsal:

```bash
rm2-backup sync-plan --config /etc/rm2-backup-test/config.toml
```

The output must be pull-only from the RM2 to Raspberry Pi storage. It must not include `--delete`.

## Run the local pipeline

After raw data already exists on the Raspberry Pi, run:

```bash
rm2-backup run-local --config config.local.toml
```

For the production-like spare-RM2 rehearsal:

```bash
rm2-backup run-local --config /etc/rm2-backup-test/config.toml
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

## Production-like rehearsal with the spare RM2

Use this sequence when you want to test on the Raspberry Pi as if it were production, while still using the spare RM2:

1. Install the repository under `/opt/rm2-pdf-backup`.
2. Create runtime folders under `/srv/rm2-backup-test`.
3. Copy `deploy/config/production.example.toml` to `/etc/rm2-backup-test/config.toml`.
4. Edit `/etc/rm2-backup-test/config.toml` so `[rm2].host` points to the spare RM2 and all `[paths]` values point under `/srv/rm2-backup-test`.
5. Run `rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl`.
6. Run `rm2-backup sync-plan --config /etc/rm2-backup-test/config.toml` and verify it is pull-only and has no `--delete`.
7. Run the approved raw-copy workflow on the Raspberry Pi self-hosted runner, or run the reviewed pull-only command manually on the Raspberry Pi.
8. Run `rm2-backup run-local --config /etc/rm2-backup-test/config.toml`.
9. Review the newest report under `/srv/rm2-backup-test/reports`.
10. Inspect `/srv/rm2-backup-test/pdf/current` for validated outputs.
11. Repeat the run to confirm unchanged documents are skipped where expected.

Do not enable the real production timer from this rehearsal. If you add a test timer later, keep it named and configured as a test service that points only at `/etc/rm2-backup-test/config.toml`.

## GitHub Actions and spare-RM2 validation

Hardware validation should run through GitHub Actions on the Raspberry Pi self-hosted runner, not from a developer Mac.

Use the manually triggered development workflows for:

- RPI runner diagnostics;
- spare-RM2 SSH smoke testing;
- raw copy validation;
- renderer probes;
- run-local validation;
- two-run/change-skip validation;
- systemd unit validation.

These workflows are development/spare-RM2 gates. Do not point them at the production or beamline RM2.

## Systemd operation

Systemd files are examples and must be reviewed on the Raspberry Pi before enablement:

- `deploy/systemd/rm2-backup-dev.service`;
- `deploy/systemd/rm2-backup-dev.timer`;
- `packaging/systemd/rm2-backup.service.example`;
- `packaging/systemd/rm2-backup.timer.example`.

Safe order:

1. Run local synthetic checks.
2. Inspect `rm2-backup sync-plan`.
3. Complete spare-RM2 GitHub Actions validation.
4. Manually start the development service on the Raspberry Pi.
5. Review the report and published outputs.
6. Enable the development timer only after the manual service run is accepted.

Production timer enablement is gated by `docs/mvp-production-deployment.md`.

## MVP production gate

Do not deploy to the production RM2 just because local tests pass. Production requires the ordered checklist in `docs/mvp-production-deployment.md`, including spare-RM2 validation, manual production dry-run on the Raspberry Pi, report review, and explicit timer enablement only after acceptance.

## Troubleshooting

If `rm2-backup plan` fails, check that the metadata directory contains synthetic or copied `*.metadata` files.

If `rm2-backup sync-plan` fails, check the TOML file has `[rm2]`, `[paths]`, and valid renderer settings.

If `rm2-backup run-local` reports failed documents, inspect the generated report before changing timers or production configuration.

If a workflow fails on the self-hosted runner, treat that as a failed gate. Fix the repository through a reviewed pull request before moving to the next deployment step.
