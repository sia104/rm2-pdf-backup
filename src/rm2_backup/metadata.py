"""Parse reMarkable xochitl metadata files.

The reMarkable document store uses UUID-based filenames. The visible folder
structure must therefore be reconstructed from metadata fields such as
``visibleName``, ``type`` and ``parent`` rather than from the raw filesystem
layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any


class MetadataParseError(ValueError):
    """Raised when a metadata file cannot be parsed safely."""


class MetadataKind(str, Enum):
    """Known high-level metadata item categories."""

    COLLECTION = "collection"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MetadataRecord:
    """A parsed RM2 metadata record.

    ``uuid`` is derived from the ``*.metadata`` filename. The remaining fields
    come from the JSON payload.
    """

    uuid: str
    visible_name: str
    raw_type: str
    kind: MetadataKind
    parent: str
    deleted: bool
    last_modified: str | None
    source_path: Path

    @property
    def is_collection(self) -> bool:
        """Return whether this record represents a folder/collection."""

        return self.kind is MetadataKind.COLLECTION

    @property
    def is_document(self) -> bool:
        """Return whether this record represents a document/notebook."""

        return self.kind is MetadataKind.DOCUMENT

    @property
    def is_in_trash(self) -> bool:
        """Return whether this record is in the RM2 trash parent."""

        return self.parent == "trash"

    @property
    def is_deleted_or_trashed(self) -> bool:
        """Return whether this item should be treated as deleted/trashed."""

        return self.deleted or self.is_in_trash


def parse_metadata_file(path: str | Path) -> MetadataRecord:
    """Parse one synthetic or copied RM2 ``*.metadata`` file.

    The parser is deliberately strict for required fields so that incomplete or
    invalid fixtures fail clearly during development.
    """

    metadata_path = Path(path)
    uuid = _uuid_from_metadata_path(metadata_path)
    payload = _read_json_object(metadata_path)

    visible_name = _required_string(payload, "visibleName", metadata_path)
    raw_type = _required_string(payload, "type", metadata_path)
    parent = _optional_string(payload, "parent", default="", path=metadata_path)
    deleted = _optional_bool(payload, "deleted", default=False, path=metadata_path)
    last_modified = _optional_string(payload, "lastModified", default=None, path=metadata_path)

    return MetadataRecord(
        uuid=uuid,
        visible_name=visible_name,
        raw_type=raw_type,
        kind=_kind_from_raw_type(raw_type),
        parent=parent,
        deleted=deleted,
        last_modified=last_modified,
        source_path=metadata_path,
    )


def scan_metadata_directory(path: str | Path) -> tuple[MetadataRecord, ...]:
    """Parse all ``*.metadata`` files directly inside a directory.

    Files are processed in sorted order to keep test results deterministic.
    """

    directory = Path(path)
    if not directory.is_dir():
        raise MetadataParseError(f"Metadata directory does not exist: {directory}")

    return tuple(parse_metadata_file(file_path) for file_path in sorted(directory.glob("*.metadata")))


def _uuid_from_metadata_path(path: Path) -> str:
    if path.suffix != ".metadata":
        raise MetadataParseError(f"Metadata file must end with .metadata: {path}")

    uuid = path.name[: -len(".metadata")]
    if not uuid:
        raise MetadataParseError(f"Metadata filename has no UUID stem: {path}")

    return uuid


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetadataParseError(f"Invalid JSON metadata file: {path}") from exc
    except OSError as exc:
        raise MetadataParseError(f"Could not read metadata file: {path}") from exc

    if not isinstance(payload, dict):
        raise MetadataParseError(f"Metadata JSON root must be an object: {path}")

    return payload


def _required_string(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise MetadataParseError(f"Required string field {key!r} missing or invalid in {path}")
    return value


def _optional_string(
    payload: dict[str, Any],
    key: str,
    *,
    default: str | None,
    path: Path,
) -> str | None:
    value = payload.get(key, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MetadataParseError(f"Optional string field {key!r} invalid in {path}")
    return value


def _optional_bool(payload: dict[str, Any], key: str, *, default: bool, path: Path) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised == "true":
            return True
        if normalised == "false":
            return False
    raise MetadataParseError(f"Optional boolean field {key!r} invalid in {path}")


def _kind_from_raw_type(raw_type: str) -> MetadataKind:
    if raw_type == "CollectionType":
        return MetadataKind.COLLECTION
    if raw_type == "DocumentType":
        return MetadataKind.DOCUMENT
    return MetadataKind.UNKNOWN
