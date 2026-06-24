# Raspberry Pi installation notes

Start with the local dry-run and placeholder renderer before enabling device access.

## Local dry-run

Run the package in a Python virtual environment, then run:

```bash
rm2-backup plan --metadata-dir tests/fixtures/synthetic_xochitl
```

## Systemd examples

Example unit files are in `packaging/systemd/`. Copy them into the systemd unit directory only after editing paths and user/group for the target Raspberry Pi.

## Safety

Use the spare RM2 first. The raw sync code is designed as a pull from the device to local storage.
