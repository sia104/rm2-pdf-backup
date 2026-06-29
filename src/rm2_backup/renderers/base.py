"""Backend interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rm2_backup.render_queue import RenderPlanItem


@dataclass(frozen=True, slots=True)
class RenderDiagnostics:
    """Structured renderer diagnostics for reporting."""

    renderer_primary: str | None = None
    renderer_final: str | None = None
    template_background: str | None = None
    highlighter_colour_mode: str | None = None
    fallback_attempted: bool = False
    fallback_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Result for one document."""

    uuid: str
    ok: bool
    output_path: Path | None
    error: str | None = None
    warning: str | None = None
    diagnostics: RenderDiagnostics = RenderDiagnostics()


class Renderer(Protocol):
    """Protocol implemented by backends."""

    def render(
        self,
        item: RenderPlanItem,
        *,
        raw_xochitl: Path,
        staging_pdf: Path,
    ) -> RenderResult:
        """Create one staged PDF."""
