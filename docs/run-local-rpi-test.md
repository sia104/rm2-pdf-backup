# RPI run-local diagnostic test

This workflow runs the local pipeline against copied test RM2 data already present on the Raspberry Pi runner.

It does not SSH to the RM2, write to the RM2, delete RM2 files, or touch production backup paths.

The workflow uses:

- raw input: `/home/k11-user/rm2-backup-dev/raw/current/xochitl`
- report output: `/home/k11-user/rm2-backup-dev/reports/run-local`
- renderer mode: `rmc-svg`

The run is diagnostic. Partial rendering is expected while `rmc` does not support every RM page. The important behaviours are:

- the pipeline completes without crashing;
- renderer failures are recorded;
- staged PDFs are only created for valid rendered outputs;
- a summary artifact is uploaded.

For malformed SVG failures, the report should include page-level diagnostics such as:

- `category=malformed_svg`;
- failing `page=...`;
- `page_bytes=...` and `svg_bytes=...`;
- `return_code=...`;
- `parse_error=...`;
- an `stderr=...` snippet from `rmc`.
