"""Plan document output paths from the visible metadata tree."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Mapping

from rm2_backup.tree import VisibleNode


class OutputPlanError(ValueError):
    """Raised when output planning cannot continue safely."""


@dataclass(frozen=True, slots=True)
class PlannedOutput:
    """A planned document output path."""

    uuid: str
    visible_path: tuple[str, ...]
    safe_relative_path: PurePosixPath


def build_output_plan(tree: Mapping[str, VisibleNode]) -> tuple[PlannedOutput, ...]:
    """Plan relative output paths for document nodes only."""

    planned: list[PlannedOutput] = []
    seen_paths: dict[PurePosixPath, str] = {}

    for uuid in sorted(tree):
        node = tree[uuid]
        if not node.is_document:
            continue
        relative_path = _document_relative_path(node)
        existing_uuid = seen_paths.get(relative_path)
        if existing_uuid is not None:
            raise OutputPlanError(
                f"Output path collision between {existing_uuid!r} and {uuid!r}: {relative_path}"
            )
        seen_paths[relative_path] = uuid
        planned.append(
            PlannedOutput(
                uuid=uuid,
                visible_path=node.visible_path,
                safe_relative_path=relative_path,
            )
        )

    return tuple(planned)


def _document_relative_path(node: VisibleNode) -> PurePosixPath:
    if not node.safe_path:
        raise OutputPlanError(f"Document {node.uuid!r} has no safe path")

    folder_parts = node.safe_path[:-1]
    file_name = f"{node.safe_path[-1]}.pdf"
    parts = (*folder_parts, file_name)
    _reject_unsafe_parts(parts)
    return PurePosixPath(*parts)


def _reject_unsafe_parts(parts: tuple[str, ...]) -> None:
    for part in parts:
        if part in {"", ".", ".."}:
            raise OutputPlanError(f"Unsafe output path segment: {part!r}")
        if "/" in part or "\\" in part:
            raise OutputPlanError(f"Output path segment contains a separator: {part!r}")
