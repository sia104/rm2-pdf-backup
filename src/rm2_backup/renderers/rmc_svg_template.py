"""Optional SVG background layer support for rmc SVG output."""

from __future__ import annotations

from pathlib import Path

from rm2_backup.pdf_compose import PdfCompositionError, compose_svg_pages_to_pdf
from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.base import RenderResult
from rm2_backup.renderers.rmc_svg import RmcSvgRenderer, summary_failure_message
from rm2_backup.template_compose import compose_svg_template_background, resolve_template_file
from rm2_backup.templates import build_template_inventory, summarise_document_templates


class TemplateRmcSvgRenderer(RmcSvgRenderer):
    """Rmc SVG renderer that can place an SVG background layer under handwriting."""

    def render(self, item: RenderPlanItem, *, raw_xochitl: Path, staging_pdf: Path) -> RenderResult:
        work_dir = staging_pdf.parent / f"{staging_pdf.stem}-svg"
        summary = self.render_svg_pages(item, raw_xochitl=raw_xochitl, work_dir=work_dir)
        if not summary.ok_for_composition:
            fallback = self.render_pdf_fallback(item, summary=summary, staging_pdf=staging_pdf)
            if fallback.ok:
                return fallback
            error = summary_failure_message(summary)
            if fallback.error:
                error = f"{error}; fallback_error={fallback.error}"
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error=error,
            )

        svg_paths = add_template_backgrounds(
            raw_xochitl=raw_xochitl,
            uuid=item.uuid,
            svg_paths=summary.usable_svg_paths,
            work_dir=work_dir,
        )
        try:
            compose_svg_pages_to_pdf(svg_paths, staging_pdf)
        except PdfCompositionError as exc:
            return RenderResult(uuid=item.uuid, ok=False, output_path=None, error=str(exc))
        return RenderResult(uuid=item.uuid, ok=True, output_path=staging_pdf)


def add_template_backgrounds(
    *,
    raw_xochitl: Path,
    uuid: str,
    svg_paths: tuple[Path, ...],
    work_dir: Path,
) -> tuple[Path, ...]:
    inventory = build_template_inventory(raw_xochitl.parent / "templates")
    summary = summarise_document_templates(raw_xochitl=raw_xochitl, uuid=uuid, inventory=inventory)
    resolution = resolve_template_file(summary, inventory)
    if resolution.template is None or resolution.template.suffix.lower() != ".svg":
        return svg_paths

    template_svg = inventory.root / resolution.template.relative_path
    output_paths: list[Path] = []
    for index, svg_path in enumerate(svg_paths, start=1):
        output_svg = work_dir / f"{index:04d}-{svg_path.stem}-background.svg"
        try:
            compose_svg_template_background(
                template_svg=template_svg,
                handwriting_svg=svg_path,
                output_svg=output_svg,
            )
        except (OSError, ValueError):
            return svg_paths
        output_paths.append(output_svg)
    return tuple(output_paths)
