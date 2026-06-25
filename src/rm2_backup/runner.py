"""Local run orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rm2_backup.config import AppConfig
from rm2_backup.manifest import Manifest, hash_document_source
from rm2_backup.metadata import scan_metadata_directory
from rm2_backup.publish import PublishError, publish_validated_pdf
from rm2_backup.render_queue import RenderPlanItem, plan_pdf_outputs
from rm2_backup.renderers.base import Renderer
from rm2_backup.renderers.external import ExternalCommandRenderer
from rm2_backup.renderers.null import PlaceholderRenderer
from rm2_backup.renderers.rmc_svg import RmcSvgRenderer
from rm2_backup.templates import TemplateProvenance, template_provenance_for_document
from rm2_backup.tree import build_visible_tree
from rm2_backup.validate import validate_pdf


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Summary of a local run."""

    planned: int
    completed: int
    skipped: int
    failed: int
    published: int = 0
    report_path: Path | None = None


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    """One document-level pipeline event for reporting."""

    uuid: str
    visible_path: tuple[str, ...]
    output_relative_path: str
    status: str
    message: str | None = None
    destination: Path | None = None
    template_provenance: TemplateProvenance | None = None


def run_local(config: AppConfig) -> PipelineResult:
    """Run the local planning, render, validate and publish pipeline."""

    source_dir = config.paths.raw_current / "xochitl"
    metadata = scan_metadata_directory(source_dir)
    tree = build_visible_tree(metadata)
    plan = plan_pdf_outputs(tree)
    renderer = _renderer_from_config(config)

    completed = 0
    skipped = 0
    failed = 0
    published = 0
    events: list[PipelineEvent] = []

    with Manifest(config.paths.database) as manifest:
        for item in plan:
            template_provenance = template_provenance_for_document(
                raw_xochitl=source_dir,
                raw_current=config.paths.raw_current,
                uuid=item.uuid,
            )
            source_hash = hash_document_source(source_dir, item.uuid)
            decision = manifest.decide(item, source_hash)
            if not decision.should_render:
                skipped += 1
                events.append(_event(item, "skipped", decision.reason, template_provenance=template_provenance))
                continue

            staged_pdf = _staged_pdf_path(config.paths.staging, item.uuid)
            result = renderer.render(item, raw_xochitl=source_dir, staging_pdf=staged_pdf)
            if not result.ok or result.output_path is None:
                failed += 1
                manifest.record_render_result(
                    item,
                    source_hash=source_hash,
                    status="failed",
                    error=result.error,
                )
                events.append(_event(item, "failed", result.error, template_provenance=template_provenance))
                continue

            validation = validate_pdf(result.output_path)
            if not validation.ok:
                failed += 1
                manifest.record_render_result(
                    item,
                    source_hash=source_hash,
                    status="failed",
                    error=validation.reason,
                )
                events.append(_event(item, "failed", validation.reason, template_provenance=template_provenance))
                continue

            try:
                publish_result = publish_validated_pdf(
                    uuid=item.uuid,
                    staged_pdf=result.output_path,
                    pdf_root=config.paths.pdf_current,
                    relative_pdf_path=item.output_relative_path,
                )
            except PublishError as exc:
                failed += 1
                manifest.record_render_result(
                    item,
                    source_hash=source_hash,
                    status="failed",
                    error=str(exc),
                )
                events.append(_event(item, "failed", str(exc), template_provenance=template_provenance))
                continue

            completed += 1
            published += 1
            manifest.record_render_result(item, source_hash=source_hash, status="ok")
            events.append(_event(item, "ok", destination=publish_result.destination, template_provenance=template_provenance))

    report_path = _write_run_report(
        config.paths.reports / "run-local-report.txt",
        planned=len(plan),
        completed=completed,
        skipped=skipped,
        failed=failed,
        published=published,
        events=events,
    )

    return PipelineResult(
        planned=len(plan),
        completed=completed,
        skipped=skipped,
        failed=failed,
        published=published,
        report_path=report_path,
    )


def _renderer_from_config(config: AppConfig) -> Renderer:
    if config.renderer.mode == "placeholder":
        return PlaceholderRenderer()
    if config.renderer.mode == "external":
        if config.renderer.command is None:
            raise ValueError("External renderer mode requires a command")
        return ExternalCommandRenderer(config.renderer.command)
    if config.renderer.mode == "rmc-svg":
        return RmcSvgRenderer(compose_command=config.renderer.command)
    raise ValueError(f"Unsupported renderer mode: {config.renderer.mode}")


def _staged_pdf_path(staging_root: Path, uuid: str) -> Path:
    return staging_root / "pdf" / f"{uuid}.pdf"


def _event(
    item: RenderPlanItem,
    status: str,
    message: str | None = None,
    *,
    destination: Path | None = None,
    template_provenance: TemplateProvenance | None = None,
) -> PipelineEvent:
    return PipelineEvent(
        uuid=item.uuid,
        visible_path=item.visible_path,
        output_relative_path=str(item.output_relative_path),
        status=status,
        message=message,
        destination=destination,
        template_provenance=template_provenance,
    )


def _write_run_report(
    path: Path,
    *,
    planned: int,
    completed: int,
    skipped: int,
    failed: int,
    published: int,
    events: list[PipelineEvent],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "RM2 PDF backup run report",
        "",
        f"planned: {planned}",
        f"completed: {completed}",
        f"skipped: {skipped}",
        f"failed: {failed}",
        f"published: {published}",
        "",
        "Documents",
    ]
    if not events:
        lines.append("- no documents processed")
    for event in events:
        visible = "/".join(event.visible_path) if event.visible_path else event.uuid
        lines.append(f"- {event.status}: {visible}")
        lines.append(f"  uuid: {event.uuid}")
        lines.append(f"  output: {event.output_relative_path}")
        if event.destination is not None:
            lines.append(f"  destination: {event.destination}")
        if event.template_provenance is not None:
            lines.append(
                "  templates: "
                f"files={event.template_provenance.file_count} "
                f"templates_json={event.template_provenance.has_templates_json} "
                f"referenced={len(event.template_provenance.referenced)} "
                f"missing={len(event.template_provenance.missing)}"
            )
            if event.template_provenance.referenced:
                lines.append(
                    "  template_references: "
                    + ", ".join(event.template_provenance.referenced)
                )
            if event.template_provenance.missing:
                lines.append(
                    "  template_warning: missing referenced template(s): "
                    + ", ".join(event.template_provenance.missing)
                )
        if event.message:
            lines.append(f"  message: {' '.join(event.message.split())}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
