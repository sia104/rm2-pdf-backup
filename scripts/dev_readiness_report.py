"""Generate a static development-readiness report for agent-led work."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


REQUIRED_DOCS = (
    "README.md",
    "AGENTS.md",
    "SPEC.md",
    "docs/development/test-plan.md",
)

RECOMMENDED_AGENT_DOCS = ("docs/development/agent-workflow.md",)

REQUIRED_TEMPLATES = (
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/feature.md",
    ".github/ISSUE_TEMPLATE/bug.md",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    status: str
    checks: tuple[CheckResult, ...]
    warnings: tuple[str, ...]

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"


def _exists(root: Path, relative_path: str) -> bool:
    return (root / relative_path).is_file()


def _read_text(root: Path, relative_path: str) -> str:
    return (root / relative_path).read_text(encoding="utf-8")


def _workflow_files(root: Path) -> tuple[Path, ...]:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return ()
    return tuple(sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml")))


def _workflow_has_trigger(text: str, trigger: str) -> bool:
    return f"{trigger}:" in text


def check_required_docs(root: Path) -> CheckResult:
    missing = [path for path in REQUIRED_DOCS if not _exists(root, path)]
    if missing:
        return CheckResult("required_docs", False, f"missing: {', '.join(missing)}")
    return CheckResult(
        "required_docs",
        True,
        "README, AGENTS, SPEC and docs/development/test-plan.md are present",
    )


def check_agent_guidance(root: Path) -> CheckResult:
    missing = [path for path in RECOMMENDED_AGENT_DOCS if not _exists(root, path)]
    if missing:
        return CheckResult("agent_workflow_docs", False, f"missing: {', '.join(missing)}")
    return CheckResult("agent_workflow_docs", True, "agent workflow guidance is present")


def check_templates(root: Path) -> CheckResult:
    missing = [path for path in REQUIRED_TEMPLATES if not _exists(root, path)]
    if missing:
        return CheckResult("github_templates", False, f"missing: {', '.join(missing)}")
    return CheckResult("github_templates", True, "issue and pull request templates are present")


def check_cloud_ci(root: Path) -> CheckResult:
    path = ".github/workflows/ci.yml"
    if not _exists(root, path):
        return CheckResult("cloud_ci", False, "missing .github/workflows/ci.yml")

    text = _read_text(root, path)
    missing = [
        command
        for command in ("ruff check .", "pytest")
        if command not in text
    ]
    if missing:
        return CheckResult("cloud_ci", False, f"missing commands: {', '.join(missing)}")
    return CheckResult("cloud_ci", True, "cloud CI runs ruff and pytest")


def check_rpi_workflows(root: Path) -> CheckResult:
    workflow_files = _workflow_files(root)
    rpi_files = []
    for path in workflow_files:
        text = path.read_text(encoding="utf-8")
        workflow_name = path.name.lower()
        if (
            "self-hosted" in text
            or workflow_name.startswith("rpi-")
            or workflow_name.startswith("rm2-")
        ):
            rpi_files.append((path, text))

    if not rpi_files:
        return CheckResult("rpi_workflows", False, "no RPI/RM2/self-hosted workflows found")

    non_dispatch = [
        str(path.relative_to(root))
        for path, text in rpi_files
        if not _workflow_has_trigger(text, "workflow_dispatch")
    ]
    if non_dispatch:
        return CheckResult(
            "rpi_workflows",
            False,
            f"missing manual trigger: {', '.join(non_dispatch)}",
        )

    return CheckResult(
        "rpi_workflows",
        True,
        f"{len(rpi_files)} RPI/RM2/self-hosted workflows include workflow_dispatch",
    )


def collect_warnings(root: Path) -> tuple[str, ...]:
    warnings: list[str] = []
    for path in _workflow_files(root):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root)
        if "self-hosted" in text and _workflow_has_trigger(text, "pull_request"):
            warnings.append(
                f"{relative} runs on self-hosted infrastructure for pull_request events"
            )
        if "self-hosted" in text and "runs-on: self-hosted" in text:
            warnings.append(f"{relative} uses broad runs-on: self-hosted labels")
        if "permissions:" not in text:
            warnings.append(f"{relative} does not declare explicit workflow permissions")
    return tuple(warnings)


def build_report(root: Path) -> ReadinessReport:
    checks = (
        check_required_docs(root),
        check_agent_guidance(root),
        check_templates(root),
        check_cloud_ci(root),
        check_rpi_workflows(root),
    )
    warnings = collect_warnings(root)
    status = "READY" if all(check.ok for check in checks) and not warnings else "NOT_READY"
    return ReadinessReport(status, checks, warnings)


def render_report(report: ReadinessReport) -> str:
    lines = [
        "# Development Readiness Report",
        "",
        f"status: {report.status}",
        "",
        "## Checks",
    ]
    for check in report.checks:
        marker = "PASS" if check.ok else "FAIL"
        lines.append(f"- {marker} {check.name}: {check.detail}")

    lines.extend(["", "## Warnings"])
    if report.warnings:
        lines.extend(f"- WARN {warning}" for warning in report.warnings)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety",
            "- This report is static repository inspection only.",
            "- It does not SSH, SCP, rsync, or access RM2 hardware.",
            "- It does not read or write backup data, PDFs, logs, databases, keys, or secrets.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report(args.root.resolve())
    rendered = render_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
