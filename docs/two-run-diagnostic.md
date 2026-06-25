# RPI two-run diagnostic

The two-run diagnostic runs `rm2-backup run-local` twice against the same copied RM2 data and the same manifest database.

Expected behaviour:

- the first run renders and publishes supported changed documents;
- the second unchanged run skips the documents that were successfully completed on the first run;
- the second unchanged run does not republish unchanged documents;
- unsupported documents remain failed rather than being published.

This verifies the incremental behaviour before enabling scheduled unattended runs.
