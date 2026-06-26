# MVP production deployment checklist

This checklist defines the minimum safe path from the development Raspberry Pi setup to a production RM2 backup timer.

Production deployment is a manual Raspberry Pi operation. Do not run SSH, SCP, or rsync to the RM2 from a developer Mac. Do not use the beamline or production RM2 until the spare-RM2 gates below pass.

## MVP scope

MVP production means:

- read-only raw copy from the production RM2 to the Raspberry Pi;
- raw files remain the recovery source of truth;
- local metadata planning reconstructs the visible folder tree;
- supported notebooks render to validated PDFs;
- failed renders are reported and do not replace previous good PDFs;
- deleted or trashed RM2 items do not delete mirror files automatically;
- the service can run unattended through a reviewed systemd timer.

MVP does not require full visual fidelity for every RM2 feature. Unsupported renderer cases must be visible in the run report.

## Go/no-go gates

Complete these gates in order:

1. `Development readiness` workflow reports `READY` on `main`.
2. Spare-RM2 raw-copy workflow succeeds on the Raspberry Pi self-hosted runner.
3. Spare-RM2 run-local workflow succeeds and writes a clear run report.
4. Spare-RM2 two-run workflow confirms unchanged documents are skipped on the second run.
5. RPI dev systemd validation workflow succeeds.
6. Dev systemd service is manually started on the Raspberry Pi and completes without touching the RM2.
7. Dev timer is enabled only after a successful manual service run.
8. Production config is created on the Raspberry Pi from `deploy/config/production.example.toml`.
9. First production raw copy is run manually on the Raspberry Pi using read-only pull commands.
10. First production `run-local` is run manually and the report is reviewed.
11. Production timer is enabled only after the manual production run is accepted.

Stop if any gate fails.

## Production config

Use `deploy/config/production.example.toml` as a template only. Copy it on the Raspberry Pi and replace placeholders locally:

```bash
sudo mkdir -p /etc/rm2-backup
sudo cp deploy/config/production.example.toml /etc/rm2-backup/config.toml
sudoedit /etc/rm2-backup/config.toml
```

Do not commit the edited production config.

The committed example intentionally contains:

- no IP address;
- no SSH key path;
- no password or token;
- no real notebook, log, database, or PDF output.

## First production dry run

On the Raspberry Pi only:

```bash
rm2-backup plan-sync --config /etc/rm2-backup/config.toml
```

Review the planned commands. They must be pull-only `rsync` commands from the RM2 to Raspberry Pi storage and must not include `--delete`.

After review, run the raw copy through the approved Raspberry Pi workflow or a manual Raspberry Pi shell. Then run:

```bash
rm2-backup run-local --config /etc/rm2-backup/config.toml
```

Review the report before enabling any timer.

## Timer enablement

Enable the production timer only after:

- raw current files exist under the production backup root;
- at least one validated PDF has been published where expected, or unsupported documents are clearly reported;
- failed renders did not replace previous good PDFs;
- the report contains the renderer mode and document-level outcomes;
- no real RM2 data, generated PDFs, logs, databases, SSH keys, IP addresses, or secrets have been committed.

## Rollback

If a production run is bad:

- disable the timer;
- keep raw backup data intact;
- inspect the run report and manifest;
- do not delete raw data or previous PDFs as a cleanup shortcut;
- fix the issue through a reviewed PR before re-enabling unattended production runs.
