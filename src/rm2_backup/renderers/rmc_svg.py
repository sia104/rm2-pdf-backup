"""Render RM page files to SVG using rmc."""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rm2_backup.pdf_compose import PdfCompositionError, compose_svg_pages_to_pdf
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
    def page_size(self) -> int:
        """Return the source page byte size, or zero if it cannot be read."""

        try:
            return self.page_path.stat().st_size
        except OSError:
            return 0

    @property
    def svg_size(self) -> int:
        """Return the SVG byte size, or zero if no SVG exists."""

        try:
            return self.svg_path.stat().st_size
        except OSError:
            return 0

    @property
    def svg_parse_error(self) -> str | None:
        """Return a concise SVG parse error for malformed SVG output."""

        if not self.has_svg:
            return None
        try:
            root = ET.parse(self.svg_path).getroot()
        except ET.ParseError as exc:
            return str(exc)
        except (OSError, UnicodeDecodeError) as exc:
            return exc.__class__.__name__
        if not root.tag.endswith("svg"):
            return f"root tag is not svg: {root.tag}"
        return None

    @property
    def is_well_formed_svg(self) -> bool:
        """Return whether the SVG is parseable XML."""

        if not self.has_svg:
            return False
        try:
            root = ET.parse(self.svg_path).getroot()
        except (ET.ParseError, OSError, UnicodeDecodeError):
            return False
        return root.tag.endswith("svg")

    @property
    def is_clean(self) -> bool:
        """Return whether rmc exited cleanly and produced parseable SVG output."""

        return self.return_code == 0 and self.is_well_formed_svg

    @property
    def is_usable(self) -> bool:
        """Return whether the SVG is suitable for PDF composition."""

        return self.is_well_formed_svg


@dataclass(frozen=True, slots=True)
class SvgRenderSummary:
    """Summary of SVG page rendering for one document."""

    uuid: str
    page_results: tuple[SvgPageResult, ...]

    @property
    def total_pages(self) -> int:
        return len(self.page_results)

    @property
    def non_empty_pages(self) -> int:
        return sum(1 for result in self.page_results if result.has_svg)

    @property
    def usable_pages(self) -> int:
        return sum(1 for result in self.page_results if result.is_usable)

    @property
    def clean_pages(self) -> int:
        return sum(1 for result in self.page_results if result.is_clean)

    @property
    def malformed_pages(self) -> int:
        return sum(1 for result in self.page_results if result.has_svg and not result.is_well_formed_svg)

    @property
    def ok_for_composition(self) -> bool:
        return self.total_pages > 0 and self.usable_pages == self.total_pages

    @property
    def usable_svg_paths(self) -> tuple[Path, ...]:
        """Return usable SVG paths in page order."""

        return tuple(result.svg_path for result in self.page_results if result.is_usable)


class RmcSvgRenderer:
    """Render RM page files to SVG using rmc.

    The renderer treats only XML-well-formed SVG as usable. This is stricter than
    checking file size because rmc can produce truncated non-empty SVG files when
    it exits with unsupported palette values.
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
            try:
                completed = self.runner(
                    [self.executable, "-t", "svg", "-o", str(svg_path), str(page_path)],
                    check=False,
                    text=True,
                    capture_output=True,
                )
            except FileNotFoundError:
                results.append(
                    SvgPageResult(
                        page_path=page_path,
                        svg_path=svg_path,
                        return_code=127,
                        stderr=f"renderer executable not found: {self.executable}",
                    )
                )
                break
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
        """Render SVG pages and compose them into a PDF."""

        work_dir = staging_pdf.parent / f"{staging_pdf.stem}-svg"
        summary = self.render_svg_pages(item, raw_xochitl=raw_xochitl, work_dir=work_dir)
        if not summary.ok_for_composition:
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error=summary_failure_message(summary),
            )

        if self.compose_command is not None:
            return _run_external_composer(
                item=item,
                page_results=summary.page_results,
                output_pdf=staging_pdf,
                command=self.compose_command,
                runner=self.runner,
            )

        try:
            compose_svg_pages_to_pdf(summary.usable_svg_paths, staging_pdf)
        except PdfCompositionError as exc:
            return RenderResult(uuid=item.uuid, ok=False, output_path=None, error=str(exc))
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


def _run_external_composer(
    *,
    item: RenderPlanItem,
    page_results: Sequence[SvgPageResult],
    output_pdf: Path,
    command: str,
    runner: Runner,
) -> RenderResult:
    completed = runner(
        _compose_argv(command, page_results, output_pdf),
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0 or not output_pdf.exists() or output_pdf.stat().st_size == 0:
        return RenderResult(
            uuid=item.uuid,
            ok=False,
            output_path=None,
            error=completed.stderr or completed.stdout or "PDF composition failed",
        )
    return RenderResult(uuid=item.uuid, ok=True, output_path=output_pdf)


def _compose_argv(command: str, page_results: Sequence[SvgPageResult], output: Path) -> list[str]:
    svg_inputs = " ".join(str(result.svg_path) for result in page_results)
    return command.format(input_svgs=svg_inputs, output=str(output)).split()


def summary_failure_message(summary: SvgRenderSummary) -> str:
    """Return a concise, categorized message for an incomplete SVG render."""

    category = _summary_failure_category(summary)
    message = (
        f"rmc SVG render incomplete for {summary.uuid}: category={category}, "
        f"usable={summary.usable_pages}/{summary.total_pages}, "
        f"non_empty={summary.non_empty_pages}, malformed={summary.malformed_pages}, "
        f"clean={summary.clean_pages}"
    )
    problem = _first_problem_page(summary)
    if problem is None:
        return message
    details = [
        f"page={problem.page_path.name}",
        f"page_bytes={problem.page_size}",
        f"svg={problem.svg_path.name}",
        f"svg_bytes={problem.svg_size}",
        f"return_code={problem.return_code}",
    ]
    parse_error = problem.svg_parse_error
    if parse_error:
        details.append(f"parse_error={_clean_detail(parse_error)}")
    if problem.stderr:
        details.append(f"stderr={_clean_detail(problem.stderr)}")
    return f"{message}, detail: {', '.join(details)}"


def _summary_failure_category(summary: SvgRenderSummary) -> str:
    if summary.total_pages == 0:
        return "no_rm_pages"
    if any("renderer executable not found:" in result.stderr for result in summary.page_results):
        return "renderer_executable_not_found"
    if summary.usable_pages == 0 and summary.non_empty_pages == 0:
        return "no_svg_output"
    if summary.malformed_pages > 0:
        return "malformed_svg"
    if summary.usable_pages < summary.total_pages:
        return "partial_svg_output"
    if summary.clean_pages < summary.total_pages:
        return "renderer_nonzero_exit"
    return "unknown"


def _first_problem_page(summary: SvgRenderSummary) -> SvgPageResult | None:
    for result in summary.page_results:
        if not result.is_usable or result.return_code != 0:
            return result
    return None


def _clean_detail(value: str, *, limit: int = 160) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."
