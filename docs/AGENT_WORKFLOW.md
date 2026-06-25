# Agent workflow

This repository uses an AI project-manager / AI developer / GitHub runner model.

The intended workflow is:

```text
User intent
  -> agent checks README, AGENTS, SPEC, TEST_PLAN, issues and PRs
  -> agent creates or updates a focused GitHub issue
  -> agent creates a branch from main
  -> agent makes the smallest safe change
  -> agent adds or updates tests
  -> agent runs local checks where possible
  -> agent opens a draft pull request
  -> GitHub Actions runs cloud CI
  -> RPI self-hosted workflows perform trusted hardware validation when needed
  -> human reviews and merges
```

## Roles

- User: describes the desired outcome and approves or merges pull requests.
- ChatGPT/Codex: plans work, writes issues, edits code, writes tests and opens PRs.
- GitHub: source of truth for issues, branches, pull requests and checks.
- Raspberry Pi self-hosted runner: only trusted path for hardware-in-the-loop tests.
- Development RM2: test target.
- Beamline/production RM2: protected target, not touched by normal development tasks.

## Normal task flow

For each task, the agent should:

1. Inspect repository instructions and existing work.
2. Create or update a focused issue.
3. Create a branch from `main`.
4. Make a small, reviewable change.
5. Add or update tests.
6. Run `ruff check .` and `pytest` where possible.
7. Push the branch.
8. Open a draft PR.
9. Fill in the PR safety checklist.
10. State whether RPI/dev-RM2 validation is required.

## Safety boundary

Agents must not SSH, SCP or rsync to the RM2 from a developer Mac. RM2 interaction should happen only through reviewed repository automation running on the Raspberry Pi self-hosted runner.

Agents must stop for human approval before production deployment, systemd service/timer changes, deletion/archive behaviour, raw backup retention policy, credential handling, or any change that weakens validation or publication safety.

## First recommended automation issue

Add a single release-readiness or dev-status workflow that reports:

- cloud CI status;
- RPI runner availability;
- dev RM2 SSH availability;
- raw copy result;
- local pipeline result;
- number of PDFs published;
- renderer failures;
- template warnings.

This should remain development-only until a separate release checklist gates deployment to the beamline RM2.
