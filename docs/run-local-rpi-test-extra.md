# RPI run-local diagnostic notes

The RPI run-local diagnostic workflow is separate from the production timer path.

It uses copied RM2 data on the runner and writes only under `/home/k11-user/rm2-backup-dev/reports/run-local`.

Success means the orchestration completes, records renderer failures, and uploads a clear summary without touching the RM2 or production backup paths.
