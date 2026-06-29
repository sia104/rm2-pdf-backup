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
from rm2_backup.renderers.rmc_svg_template import TemplateRmcSvgRenderer
from rm2_backup.templates import build_template_inventory, summarise_document_templates
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


def run_local(config: AppConfig) -> PipelineResult:
    """Run the local planning, render, validate and publish pipeline."""

    source_dir = config.paths.raw_current / "xochitl"
    template_inventory = build_template_inventory(config.paths.raw_current / "templates")
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
            template_message = summarise_document_templates(
                raw_xochitl=source_dir,
                uuid=item.uuid,
                inventory=template_inventory,
            ).message
            source_hash = hash_document_source(source_dir, item.uuid)
            decision = manifest.decide(item, source_hash)
            if not decision.should_render:
                skipped += 1
                events.append(_event(item, "skipped", _join_messages(decision.reason, template_message)))
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
                events.append(_event(item, "failed", _join_messages(result.error, template_message)))
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
                events.append(_event(item, "failed", _join_messages(validation.reason, template_message)))
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
                events.append(_event(item, "failed", _join_messages(str(exc), template_message)))
                continue

            completed += 1
            published += 1
            manifest.record_render_result(item, source_hash=source_hash, status="ok")
            events.append(
                _event(
                    item,
                    "ok",
                    _join_messages(result.warning, template_message),
                    destination=publish_result.destination,
                )
            )

    report_path = _write_run_report(
        config.paths.reports / "run-local-report.txt",
        planned=len(plan),
        completed=completed,
        skipped=skipped,
        failed=failed,
        published=published,
        renderer_mode=config.renderer.mode,
        template_count=template_inventory.count,
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
        if config.renderer.include_templates:
            return TemplateRmcSvgRenderer(compose_command=config.renderer.command)
        return RmcSvgRenderer(compose_command=config.renderer.command)
    raise ValueError(f"Unsupported renderer mode: {config.renderer.mode}")


def _staged_pdf_path(staging_root: Path, uuid: str) -> Path:
    return staging_root / "pdf" / f"{uuid}.pdf"


def _join_messages(*messages: str | None) -> str:
    return "; ".join(message for message in messages if message)


def _event(
    item: RenderPlanItem,
    status: str,
    message: str | None = None,
    *,
    destination: Path | None = None,
) -> PipelineEvent:
    return PipelineEvent(
        uuid=item.uuid,
        visible_path=item.visible_path,
        output_relative_path=str(item.output_relative_path),
        status=status,
        message=message,
        destination=destination,
    )


def _write_run_report(
    path: Path,
    *,
    planned: int,
    completed: int,
    skipped: int,
    failed: int,
    published: int,
    renderer_mode: str | None = None,
    template_count: int | None = None,
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
    ]
    if renderer_mode is not None:
        lines.append(f"renderer: {renderer_mode}")
    if template_count is not None:
        lines.append(f"templates_file_count: {template_count}")
    lines.extend(["", "Documents"])
    if not events:
        lines.append("- no documents processed")
    for event in events:
        visible = "/".join(event.visible_path) if event.visible_path else event.uuid
        lines.append(f"- {event.status}: {visible}")
        lines.append(f"  uuid: {event.uuid}")
        lines.append(f"  output: {event.output_relative_path}")
        if event.destination is not None:
            lines.append(f"  destination: {event.destination}")
        if event.message:
            lines.append(f"  message: {' '.join(event.message.split())}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
