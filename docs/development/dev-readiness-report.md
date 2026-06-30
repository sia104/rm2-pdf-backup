# Development readiness report

The `Development readiness` workflow generates a static report describing whether the repository is ready for the AI project-manager / AI developer / GitHub runner model.

It checks:

- required guidance files: `README.md`, `AGENTS.md`, `SPEC.md`, and `docs/development/test-plan.md`;
- recommended agent workflow guidance in `docs/development/agent-workflow.md`;
- GitHub issue and pull request templates;
- cloud CI coverage for `ruff check .` and `pytest`;
- RPI/RM2/self-hosted workflows that can be started manually with `workflow_dispatch`;
- warnings for self-hosted workflows that run on pull requests, broad `runs-on: self-hosted` labels, and missing explicit workflow permissions.

The workflow is intentionally static. It runs on `ubuntu-latest`, does not SSH, SCP, rsync, or access RM2 hardware, and does not read or write backup data, PDFs, logs, databases, keys, or secrets.

The report status is:

- `READY` when all checks pass and no warnings are present;
- `NOT_READY` when required pieces are missing or warning conditions remain.

The workflow uploads `readiness-report.md` as the `development-readiness-report` artifact and also writes it to the GitHub Actions step summary.
