"""Render RM page files to SVG using rmc."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.base import RenderResult

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class SvgPageResult:
    """Result from rendering one RM page to SVG."""

    page_path: Path
    svg_path: Path
    return_code: int
    stderr: str

    @property
    def has_svg(self) -> bool:
        """Return whether rmc produced a non-empty SVG file."""

        return self.svg_path.exists() and self.svg_path.stat().st_size > 0

    @property
    def is_clean(self) -> bool:
        """Return whether rmc exited cleanly and produced SVG output."""

        return self.return_code == 0 and self.has_svg

    @property
    def is_usable(self) -> bool:
        """Return whether the SVG is usable despite a non-zero exit."""

        return self.has_svg


@dataclass(frozen=True, slots=True)
class SvgRenderSummary:
    """Summary of SVG page rendering for one document."""

    uuid: str
    page_results: tuple[SvgPageResult, ...]

    @property
    def total_pages(self) -> int:
        return len(self.page_results)

    @property
    def usable_pages(self) -> int:
        return sum(1 for result in self.page_results if result.is_usable)

    @property
    def clean_pages(self) -> int:
        return sum(1 for result in self.page_results if result.is_clean)

    @property
    def ok_for_composition(self) -> bool:
        return self.total_pages > 0 and self.usable_pages == self.total_pages


class RmcSvgRenderer:
    """Render RM page files to SVG using rmc.

    The renderer treats non-empty SVG output as usable even when rmc returns a
    non-zero exit code. This handles the current observed behaviour where some
    pages render usable SVG while rmc reports unsupported palette values.
    """

    def __init__(
        self,
        *,
        executable: str = "rmc",
        runner: Runner = subprocess.run,
        compose_command: str | None = None,
    ) -> None:
        self.executable = executable
        self.runner = runner
        self.compose_command = compose_command

    def render_svg_pages(self, item: RenderPlanItem, *, raw_xochitl: Path, work_dir: Path) -> SvgRenderSummary:
        """Render all known RM pages for a document to SVG files."""

        page_paths = find_rm_page_files(raw_xochitl, item.uuid)
        work_dir.mkdir(parents=True, exist_ok=True)
        results: list[SvgPageResult] = []
        for index, page_path in enumerate(page_paths, start=1):
            svg_path = work_dir / f"{index:04d}-{page_path.stem}.svg"
            completed = self.runner(
                [self.executable, "-t", "svg", "-o", str(svg_path), str(page_path)],
                check=False,
                text=True,
                capture_output=True,
            )
            results.append(
                SvgPageResult(
                    page_path=page_path,
                    svg_path=svg_path,
                    return_code=completed.returncode,
                    stderr=completed.stderr,
                )
            )
        return SvgRenderSummary(uuid=item.uuid, page_results=tuple(results))

    def render(self, item: RenderPlanItem, *, raw_xochitl: Path, staging_pdf: Path) -> RenderResult:
        """Render SVG pages and optionally compose them into a PDF."""

        work_dir = staging_pdf.parent / f"{staging_pdf.stem}-svg"
        summary = self.render_svg_pages(item, raw_xochitl=raw_xochitl, work_dir=work_dir)
        if not summary.ok_for_composition:
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error=_summary_error(summary),
            )
        if self.compose_command is None:
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error="SVG pages rendered, but PDF composition is not configured",
            )
        completed = self.runner(
            _compose_argv(self.compose_command, summary.page_results, staging_pdf),
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0 or not staging_pdf.exists() or staging_pdf.stat().st_size == 0:
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error=completed.stderr or completed.stdout or "PDF composition failed",
            )
        return RenderResult(uuid=item.uuid, ok=True, output_path=staging_pdf)


def find_rm_page_files(raw_xochitl: Path, uuid: str) -> tuple[Path, ...]:
    """Find RM page files for a document in stable page order where possible."""

    ordered = _ordered_pages_from_content(raw_xochitl, uuid)
    if ordered:
        return ordered

    document_dir = raw_xochitl / uuid
    if document_dir.is_dir():
        pages = tuple(sorted(document_dir.rglob("*.rm")))
        if pages:
            return pages

    return tuple(sorted(raw_xochitl.glob(f"{uuid}*.rm")))


def _ordered_pages_from_content(raw_xochitl: Path, uuid: str) -> tuple[Path, ...]:
    content_path = raw_xochitl / f"{uuid}.content"
    if not content_path.is_file():
        return ()
    try:
        payload = json.loads(content_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ()

    pages = payload.get("pages")
    if not isinstance(pages, list):
        return ()

    found: list[Path] = []
    for page in pages:
        if not isinstance(page, str) or page == "":
            continue
        candidates = (
            raw_xochitl / uuid / f"{page}.rm",
            raw_xochitl / f"{page}.rm",
            raw_xochitl / f"{uuid}-{page}.rm",
        )
        for candidate in candidates:
            if candidate.is_file():
                found.append(candidate)
                break
    return tuple(found)


def _compose_argv(command: str, page_results: Sequence[SvgPageResult], output: Path) -> list[str]:
    svg_inputs = " ".join(str(result.svg_path) for result in page_results)
    return command.format(input_svgs=svg_inputs, output=str(output)).split()


def _summary_error(summary: SvgRenderSummary) -> str:
    return (
        f"rmc SVG render incomplete for {summary.uuid}: "
        f"usable={summary.usable_pages}/{summary.total_pages}, clean={summary.clean_pages}"
    )
