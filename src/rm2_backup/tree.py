"""Build a visible folder tree from parsed metadata records."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from rm2_backup.metadata import MetadataKind, MetadataRecord


class TreeBuildError(ValueError):
    """Raised when visible tree reconstruction cannot continue safely."""


@dataclass(frozen=True, slots=True)
class VisibleNode:
    """A metadata record with resolved visible path information."""

    uuid: str
    visible_name: str
    safe_name: str
    kind: MetadataKind
    parent: str
    visible_path: tuple[str, ...]
    safe_path: tuple[str, ...]

    @property
    def is_collection(self) -> bool:
        """Return whether this node represents a folder/collection."""

        return self.kind is MetadataKind.COLLECTION

    @property
    def is_document(self) -> bool:
        """Return whether this node represents a document/notebook."""

        return self.kind is MetadataKind.DOCUMENT


def build_visible_tree(records: tuple[MetadataRecord, ...]) -> dict[str, VisibleNode]:
    """Build visible paths for active metadata records.

    Records marked deleted or stored in the trash parent are excluded. Missing
    parents and parent cycles are reported explicitly.
    """

    active_records = tuple(
        record for record in records if not record.is_deleted_or_trashed
    )
    by_uuid = _records_by_uuid(active_records)
    child_name_counts = _child_name_counts(active_records)
    resolved: dict[str, VisibleNode] = {}

    for record in active_records:
        _resolve_record(record, by_uuid, child_name_counts, resolved, stack=())

    return resolved


def sanitise_path_segment(name: str) -> str:
    """Return a safe filesystem path segment derived from a visible name."""

    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.rstrip(" .")
    if cleaned in {"", ".", ".."}:
        return "untitled"
    return cleaned


def _resolve_record(
    record: MetadataRecord,
    by_uuid: dict[str, MetadataRecord],
    child_name_counts: Counter[tuple[str, str]],
    resolved: dict[str, VisibleNode],
    *,
    stack: tuple[str, ...],
) -> VisibleNode:
    if record.uuid in resolved:
        return resolved[record.uuid]
    if record.uuid in stack:
        cycle = " -> ".join((*stack, record.uuid))
        raise TreeBuildError(f"Metadata parent cycle detected: {cycle}")

    stack = (*stack, record.uuid)
    safe_name = _safe_name_for_record(record, child_name_counts)

    if record.parent == "":
        visible_parent_path: tuple[str, ...] = ()
        safe_parent_path: tuple[str, ...] = ()
    else:
        parent_record = by_uuid.get(record.parent)
        if parent_record is None:
            raise TreeBuildError(
                f"Missing parent {record.parent!r} for metadata record {record.uuid!r}"
            )
        parent_node = _resolve_record(
            parent_record,
            by_uuid,
            child_name_counts,
            resolved,
            stack=stack,
        )
        visible_parent_path = parent_node.visible_path
        safe_parent_path = parent_node.safe_path

    node = VisibleNode(
        uuid=record.uuid,
        visible_name=record.visible_name,
        safe_name=safe_name,
        kind=record.kind,
        parent=record.parent,
        visible_path=(*visible_parent_path, record.visible_name),
        safe_path=(*safe_parent_path, safe_name),
    )
    resolved[record.uuid] = node
    return node


def _records_by_uuid(records: tuple[MetadataRecord, ...]) -> dict[str, MetadataRecord]:
    by_uuid: dict[str, MetadataRecord] = {}
    for record in records:
        if record.uuid in by_uuid:
            raise TreeBuildError(f"Duplicate metadata UUID: {record.uuid}")
        by_uuid[record.uuid] = record
    return by_uuid


def _child_name_counts(records: tuple[MetadataRecord, ...]) -> Counter[tuple[str, str]]:
    return Counter(
        (record.parent, sanitise_path_segment(record.visible_name)) for record in records
    )


def _safe_name_for_record(
    record: MetadataRecord,
    child_name_counts: Counter[tuple[str, str]],
) -> str:
    safe_name = sanitise_path_segment(record.visible_name)
    if child_name_counts[(record.parent, safe_name)] == 1:
        return safe_name
    return f"{safe_name} [{record.uuid[:8]}]"
