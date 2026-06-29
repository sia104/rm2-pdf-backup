"""Read-only raw synchronisation planning and execution."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rm2_backup.config import AppConfig

XOCHITL_SOURCE = "/home/root/.local/share/remarkable/xochitl/"
TEMPLATES_SOURCE = "/usr/share/remarkable/templates/"


class RawSyncError(RuntimeError):
    """Raised when raw sync fails."""


@dataclass(frozen=True, slots=True)
class SyncCommand:
    """A planned rsync command."""

    label: str
    argv: tuple[str, ...]
    destination: Path


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Result from one rsync command."""

    label: str
    return_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class RawSyncReport:
    """Combined result from raw sync."""

    results: tuple[SyncResult, ...]

    @property
    def ok(self) -> bool:
        """Return whether all rsync commands completed successfully."""

        return all(result.return_code == 0 for result in self.results)


def plan_raw_sync(config: AppConfig) -> tuple[SyncCommand, ...]:
    """Plan read-only rsync pulls from the RM2 to local raw storage."""

    xochitl_dest = config.paths.raw_current / "xochitl"
    templates_dest = config.paths.raw_current / "templates"
    return (
        SyncCommand(
            label="xochitl",
            argv=_rsync_argv(config, XOCHITL_SOURCE, xochitl_dest),
            destination=xochitl_dest,
        ),
        SyncCommand(
            label="templates",
            argv=_rsync_argv(config, TEMPLATES_SOURCE, templates_dest),
            destination=templates_dest,
        ),
    )


def run_raw_sync(config: AppConfig) -> RawSyncReport:
    """Run read-only rsync pulls into local raw storage."""

    results: list[SyncResult] = []
    for command in plan_raw_sync(config):
        command.destination.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            command.argv,
            check=False,
            text=True,
            capture_output=True,
        )
        results.append(
            SyncResult(
                label=command.label,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
    report = RawSyncReport(results=tuple(results))
    if not report.ok:
        failed = ", ".join(result.label for result in report.results if result.return_code != 0)
        raise RawSyncError(f"Raw sync failed for: {failed}")
    return report


def _rsync_argv(config: AppConfig, source_path: str, destination: Path) -> tuple[str, ...]:
    if config.rm2.ssh_alias:
        remote = f"{config.rm2.host}:{source_path}"
        ssh_parts = ["ssh"]
    else:
        remote = f"{config.rm2.user}@{config.rm2.host}:{source_path}"
        ssh_parts = ["ssh", "-p", str(config.rm2.port)]
        if config.rm2.ssh_key is not None:
            ssh_parts.extend(["-i", str(config.rm2.ssh_key)])

    return (
        "rsync",
        "-a",
        "--checksum",
        "--partial",
        "--safe-links",
        "-e",
        " ".join(ssh_parts),
        remote,
        f"{destination}/",
    )


def format_sync_plan(commands: Sequence[SyncCommand]) -> str:
    """Return a human-readable sync plan."""

    lines = ["Planned raw sync commands:"]
    for command in commands:
        lines.append(f"{command.label}: {' '.join(command.argv)}")
    return "\n".join(lines)
