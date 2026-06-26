# Raspberry Pi dev systemd deployment

This is the first unattended-run deployment target for the Raspberry Pi dev/test setup. It intentionally uses development paths only.

## Safety model

The dev service runs only the local pipeline:

```bash
rm2-backup run-local --config /home/k11-user/rm2-backup-dev/config/dev.toml
```

It does not SSH to the RM2 and does not copy raw files. Raw copying from the test RM2 is still performed only by the explicit diagnostic workflow or by a manual read-only sync command.

## Dev paths

```text
/home/k11-user/rm2-backup-dev/
  raw/current/xochitl/
  raw/current/templates/
  pdf/current/
  staging/
  db/rm2-backup.sqlite
  reports/
  logs/
  config/dev.toml
  rm2-pdf-backup/
  venv/
```

## Install manually on the RPI

From a checkout of this repository on the RPI:

```bash
mkdir -p /home/k11-user/rm2-backup-dev/config
cp deploy/config/dev.example.toml /home/k11-user/rm2-backup-dev/config/dev.toml

sudo cp deploy/systemd/rm2-backup-dev.service /etc/systemd/system/rm2-backup-dev.service
sudo cp deploy/systemd/rm2-backup-dev.timer /etc/systemd/system/rm2-backup-dev.timer
sudo systemctl daemon-reload
```

## First manual test

```bash
sudo systemctl start rm2-backup-dev.service
systemctl status rm2-backup-dev.service --no-pager
journalctl -u rm2-backup-dev.service -n 100 --no-pager
```

Expected behaviour:

- supported changed documents are rendered and published under `pdf/current`;
- unsupported documents are recorded as failed;
- previous valid PDFs are preserved;
- a report is written under `reports/`.

## Enable the timer only after manual success

```bash
sudo systemctl enable --now rm2-backup-dev.timer
systemctl list-timers rm2-backup-dev.timer --no-pager
```

Do not use production paths until the dev timer has completed multiple runs successfully.
