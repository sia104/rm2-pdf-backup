import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dev_readiness_report.py"
SPEC = importlib.util.spec_from_file_location("dev_readiness_report", SCRIPT_PATH)
assert SPEC is not None
dev_readiness_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = dev_readiness_report
SPEC.loader.exec_module(dev_readiness_report)

build_report = dev_readiness_report.build_report
render_report = dev_readiness_report.render_report


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_ready_repo(root: Path) -> None:
    for name in ("README.md", "AGENTS.md", "SPEC.md", "docs/development/test-plan.md"):
        write(root / name, name)
    write(root / "docs" / "AGENT_WORKFLOW.md", "workflow")
    write(root / ".github" / "pull_request_template.md", "template")
    write(root / ".github" / "ISSUE_TEMPLATE" / "feature.md", "feature")
    write(root / ".github" / "ISSUE_TEMPLATE" / "bug.md", "bug")
    write(
        root / ".github" / "workflows" / "ci.yml",
        """
name: CI
permissions:
  contents: read
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check .
      - run: pytest
""",
    )
    write(
        root / ".github" / "workflows" / "rpi-dev.yml",
        """
name: RPI dev
permissions:
  contents: read
on:
  workflow_dispatch:
jobs:
  test:
    runs-on: [self-hosted, rpi, rm2, dev]
    steps:
      - run: echo static
""",
    )


def test_ready_repo_reports_ready(tmp_path: Path) -> None:
    make_ready_repo(tmp_path)

    report = build_report(tmp_path)

    assert report.status == "READY"
    assert report.is_ready
    assert report.warnings == ()
    assert "status: READY" in render_report(report)


def test_missing_templates_are_reported(tmp_path: Path) -> None:
    make_ready_repo(tmp_path)
    (tmp_path / ".github" / "pull_request_template.md").unlink()

    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    template_check = next(check for check in report.checks if check.name == "github_templates")
    assert not template_check.ok
    assert ".github/pull_request_template.md" in template_check.detail


def test_cloud_ci_is_not_classified_as_rpi_workflow(tmp_path: Path) -> None:
    make_ready_repo(tmp_path)
    (tmp_path / ".github" / "workflows" / "rpi-dev.yml").unlink()

    report = build_report(tmp_path)

    rpi_check = next(check for check in report.checks if check.name == "rpi_workflows")
    assert not rpi_check.ok
    assert "no RPI/RM2/self-hosted workflows found" in rpi_check.detail


def test_self_hosted_pull_request_workflow_is_warning(tmp_path: Path) -> None:
    make_ready_repo(tmp_path)
    write(
        tmp_path / ".github" / "workflows" / "rpi-pr.yml",
        """
name: RPI PR
on:
  workflow_dispatch:
  pull_request:
jobs:
  test:
    runs-on: self-hosted
    steps:
      - run: echo static
""",
    )

    report = build_report(tmp_path)

    assert report.status == "NOT_READY"
    assert any("pull_request events" in warning for warning in report.warnings)
    assert any("broad runs-on: self-hosted labels" in warning for warning in report.warnings)
