# RPI run-local diagnostic notes

The RPI `run-local` diagnostic workflow is intentionally separate from the production timer path.

It uses copied RM2 data already present on the runner and writes only to the development report area under `/home/k11-user/rm2-backup-dev/reports/run-local`.

The expected first-pass result is not necessarily full document coverage. At this stage, success means the orchestration completes, records renderer failures, and produces a clear summary without touching the RM2 or production backup paths.
