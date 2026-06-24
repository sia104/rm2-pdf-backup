"""Plan document render outputs without rendering or writing files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from rm2_backup.metadata import MetadataKind
from rm2_backup.tree import VisibleNode


@dataclass(frozen=True, slots=True)
class RenderPlanItem:
    """A document scheduled for future PDF rendering."""

    uuid: str
    visible_name: str
    visible_path: tuple[str, ...]
    output_relative_path: PurePosixPath


def plan_pdf_outputs(tree: dict[str, VisibleNode]) -> tuple[RenderPlanItem, ...]:
    """Return deterministic planned PDF output paths for document nodes only."""

    items: list[RenderPlanItem] = []
    for uuid, node in sorted(tree.items(), key=lambda item: item[1].safe_path):
        if node.kind is not MetadataKind.DOCUMENT:
            continue
        items.append(
            RenderPlanItem(
                uuid=uuid,
                visible_name=node.visible_name,
                visible_path=node.visible_path,
                output_relative_path=_pdf_path_for_node(node),
            )
        )
    return tuple(items)


def _pdf_path_for_node(node: VisibleNode) -> PurePosixPath:
    if not node.safe_path:
        raise ValueError(f"Document node has no safe path: {node.uuid}")

    *folders, filename = node.safe_path
    pdf_name = f"{filename}.pdf"
    if not folders:
        return PurePosixPath(pdf_name)
    return PurePosixPath(*folders, pdf_name)
