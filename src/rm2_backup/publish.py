"""Plan PDF mirror publication paths without writing files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from rm2_backup.tree import VisibleNode


class PublishPlanError(ValueError):
    """Raised when PDF mirror path planning cannot continue safely."""


@dataclass(frozen=True, slots=True)
class PdfMirrorPlan:
    """A planned PDF output for one visible document."""

    uuid: str
    visible_path: tuple[str, ...]
    relative_pdf_path: PurePosixPath


def plan_pdf_mirror_paths(tree: dict[str, VisibleNode]) -> tuple[PdfMirrorPlan, ...]:
    """Plan relative PDF paths for visible documents.

    This function is deliberately read-only: it does not create directories,
    write PDFs, remove files, or inspect the filesystem.
    """

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
