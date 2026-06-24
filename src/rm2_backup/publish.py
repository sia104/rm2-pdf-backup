"""Atomic PDF publication helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shutil

from rm2_backup.tree import VisibleNode
from rm2_backup.validate import PdfValidationResult, validate_pdf


class PublishPlanError(ValueError):
    """Raised when PDF mirror path planning cannot continue safely."""


class PublishError(RuntimeError):
    """Raised when a validated PDF cannot be published safely."""


@dataclass(frozen=True, slots=True)
class PdfMirrorPlan:
    """A planned PDF output for one visible document."""

    uuid: str
    visible_path: tuple[str, ...]
    relative_pdf_path: PurePosixPath


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Result of publishing one PDF."""

    uuid: str
    destination: Path
    validation: PdfValidationResult


def plan_pdf_mirror_paths(tree: dict[str, VisibleNode]) -> tuple[PdfMirrorPlan, ...]:
    """Plan relative PDF paths for visible documents."""

    plans: list[PdfMirrorPlan] = []
    used_paths: dict[PurePosixPath, str] = {}

    for node in sorted(tree.values(), key=lambda item: item.safe_path):
        if not node.is_document:
            continue

        relative_pdf_path = _pdf_path_for_node(node)
        existing_uuid = used_paths.get(relative_pdf_path)
        if existing_uuid is not None:
            raise PublishPlanError(
                "PDF mirror path collision for "
                f"{relative_pdf_path!s}: {existing_uuid!r} and {node.uuid!r}"
            )
        used_paths[relative_pdf_path] = node.uuid
        plans.append(
            PdfMirrorPlan(
                uuid=node.uuid,
                visible_path=node.visible_path,
                relative_pdf_path=relative_pdf_path,
            )
        )

    return tuple(plans)


def publish_validated_pdf(
    *,
    uuid: str,
    staged_pdf: Path,
    pdf_root: Path,
    relative_pdf_path: PurePosixPath,
) -> PublishResult:
    """Validate and atomically publish a staged PDF into the mirror root."""

    validation = validate_pdf(staged_pdf)
    if not validation.ok:
        raise PublishError(f"Refusing to publish invalid PDF for {uuid}: {validation.reason}")

    destination = pdf_root.joinpath(*relative_pdf_path.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_destination = destination.with_name(f".{destination.name}.tmp")
    shutil.copy2(staged_pdf, temp_destination)
    temp_destination.replace(destination)
    return PublishResult(uuid=uuid, destination=destination, validation=validation)


def _pdf_path_for_node(node: VisibleNode) -> PurePosixPath:
    if node.safe_path == ():
        raise PublishPlanError(f"Document {node.uuid!r} has no safe path")

    *parent_segments, document_name = node.safe_path
    filename = _pdf_filename(document_name)
    return PurePosixPath(*parent_segments, filename)


def _pdf_filename(stem: str) -> str:
    if stem.lower().endswith(".pdf"):
        return stem
    return f"{stem}.pdf"
