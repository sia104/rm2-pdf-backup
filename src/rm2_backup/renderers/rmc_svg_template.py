"""Optional template background layer support for rmc SVG output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rm2_backup.pdf_compose import PdfCompositionError, compose_svg_pages_to_pdf
from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.base import RenderDiagnostics, RenderResult
from rm2_backup.renderers.rmc_svg import RmcSvgRenderer, summary_failure_message
from rm2_backup.template_compose import compose_template_background, resolve_template_file
from rm2_backup.templates import build_template_inventory, summarise_document_templates


@dataclass(frozen=True, slots=True)
class TemplateBackgroundResult:
    svg_paths: tuple[Path, ...]
    warning: str | None = None


class TemplateRmcSvgRenderer(RmcSvgRenderer):
    """Rmc SVG renderer that can place a template background layer under handwriting."""

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
                diagnostics=self._diagnostics(
                    renderer_final="rmc-svg",
                    fallback_attempted=fallback.diagnostics.fallback_attempted,
                    fallback_reason=fallback.diagnostics.fallback_reason,
                ),
            )

        background = add_template_backgrounds(
            raw_xochitl=raw_xochitl,
            uuid=item.uuid,
            svg_paths=summary.usable_svg_paths,
            work_dir=work_dir,
        )
        try:
            compose_svg_pages_to_pdf(background.svg_paths, staging_pdf)
        except PdfCompositionError as exc:
            return RenderResult(
                uuid=item.uuid,
                ok=False,
                output_path=None,
                error=str(exc),
                diagnostics=self._template_diagnostics(background.warning),
            )
        return RenderResult(
            uuid=item.uuid,
            ok=True,
            output_path=staging_pdf,
            warning=background.warning,
            diagnostics=self._template_diagnostics(background.warning),
        )

    def _template_diagnostics(self, warning: str | None) -> RenderDiagnostics:
        template_background = None
        if warning and warning.startswith("template_background="):
            template_background = warning.split("=", 1)[1]
        return RenderDiagnostics(
            renderer_primary="rmc-svg",
            renderer_final="rmc-svg",
            template_background=template_background,
            highlighter_colour_mode="unknown",
        )


def add_template_backgrounds(
    *,
    raw_xochitl: Path,
    uuid: str,
    svg_paths: tuple[Path, ...],
    work_dir: Path,
) -> TemplateBackgroundResult:
    inventory = build_template_inventory(raw_xochitl.parent / "templates")
    summary = summarise_document_templates(raw_xochitl=raw_xochitl, uuid=uuid, inventory=inventory)
    resolution = resolve_template_file(summary, inventory)
    if resolution.template is None:
        warning = "template_background=omitted" if summary.references else None
        return TemplateBackgroundResult(svg_paths=svg_paths, warning=warning)

    template_asset = inventory.root / resolution.template.relative_path
    output_paths: list[Path] = []
    for index, svg_path in enumerate(svg_paths, start=1):
        output_svg = work_dir / f"{index:04d}-{svg_path.stem}-background.svg"
        try:
            compose_template_background(
                template_asset=template_asset,
                handwriting_svg=svg_path,
                output_svg=output_svg,
            )
        except (OSError, ValueError):
            return TemplateBackgroundResult(svg_paths=svg_paths, warning="template_background=omitted")
        output_paths.append(output_svg)
    return TemplateBackgroundResult(
        svg_paths=tuple(output_paths),
        warning=f"template_background={resolution.template.suffix.lower().lstrip('.')}",
    )
