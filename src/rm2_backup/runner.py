"""Local run orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rm2_backup.config import AppConfig
from rm2_backup.manifest import Manifest, hash_document_source
from rm2_backup.metadata import scan_metadata_directory
from rm2_backup.render_queue import plan_pdf_outputs
from rm2_backup.renderers.null import PlaceholderRenderer
from rm2_backup.tree import build_visible_tree
from rm2_backup.validate import validate_pdf


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Summary of a local run."""

    planned: int
    completed: int
    skipped: int
    failed: int


def run_local(config: AppConfig) -> PipelineResult:
    """Run the local planning and placeholder-render pipeline."""

    source_dir = config.paths.raw_current / "xochitl"
    metadata = scan_metadata_directory(source_dir)
    tree = build_visible_tree(metadata)
    plan = plan_pdf_outputs(tree)
    renderer = PlaceholderRenderer()

    completed = 0
    skipped = 0
    failed = 0

    with Manifest(config.paths.database) as manifest:
        for item in plan:
            source_hash = hash_document_source(source_dir, item.uuid)
            decision = manifest.decide(item, source_hash)
            if not decision.should_render:
                skipped += 1
                continue

            staged_pdf = _staged_pdf_path(config.paths.staging, item.uuid)
            result = renderer.render(item, raw_xochitl=source_dir, staging_pdf=staged_pdf)
            if not result.ok or result.output_path is None:
                failed += 1
                manifest.record_render_result(item, source_hash=source_hash, status="failed")
                continue

            validation = validate_pdf(result.output_path)
            if validation.ok:
                completed += 1
                manifest.record_render_result(item, source_hash=source_hash, status="ok")
            else:
                failed += 1
                manifest.record_render_result(
                    item,
                    source_hash=source_hash,
                    status="failed",
                    error=validation.reason,
                )

    return PipelineResult(
        planned=len(plan),
        completed=completed,
        skipped=skipped,
        failed=failed,
    )


def _staged_pdf_path(staging_root: Path, uuid: str) -> Path:
    return staging_root / "pdf" / f"{uuid}.pdf"
