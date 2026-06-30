# RPI raw-copy diagnostic

The raw-copy diagnostic performs a read-only pull from the test RM2 into the Raspberry Pi development backup area, then runs the local PDF pipeline.

Safety constraints:

- no writes to the RM2;
- no deletes on the RM2;
- no `rsync --delete`;
- copied raw data is written only under `/home/k11-user/rm2-backup-dev/raw/current`;
- rendered PDFs are written only under the workflow report area.

This checks the complete test path from RM2 raw files to validated local PDFs before deploying a scheduled service.
