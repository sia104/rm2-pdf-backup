"""External command renderer adapter."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.base import RenderResult


class ExternalCommandRenderer:
    """Invoke a configured command template for real rendering experiments.

    The command template may contain ``{uuid}``, ``{raw_xochitl}`` and
    ``{output}`` placeholders. This keeps the core pipeline independent of the
    specific RM2 renderer chosen for deployment testing.
    """

    def __init__(self, command_template: str) -> None:
        self.command_template = command_template

    def render(self, item: RenderPlanItem, *, raw_xochitl: Path, staging_pdf: Path) -> RenderResult:
        """Render one document by invoking the configured command."""

        staging_pdf.parent.mkdir(parents=True, exist_ok=True)
        command = self.command_template.format(
            uuid=item.uuid,
            raw_xochitl=str(raw_xochitl),
            output=str(staging_pdf),
        )
        completed = subprocess.run(
            shlex.split(command),
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error=completed.stderr or completed.stdout,
            )
        return RenderResult(uuid=item.uuid, ok=True, output_path=staging_pdf)
