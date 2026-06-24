from enum import StrEnum
from pathlib import Path


class MetadataParseError(ValueError): ...


class MetadataKind(StrEnum):
    COLLECTION = "collection"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class MetadataRecord:
    uuid: str
    visible_name: str
    raw_type: str
    kind: MetadataKind
    parent: str
    deleted: bool
    last_modified: str | None
    source_path: Path

    def __init__(
        self,
        *,
        uuid: str,
        visible_name: str,
        raw_type: str,
        kind: MetadataKind,
        parent: str,
        deleted: bool,
        last_modified: str | None,
        source_path: Path,
    ) -> None: ...

    @property
    def is_collection(self) -> bool: ...

    @property
    def is_document(self) -> bool: ...

    @property
    def is_in_trash(self) -> bool: ...

    @property
    def is_deleted_or_trashed(self) -> bool: ...


def parse_metadata_file(path: str | Path) -> MetadataRecord: ...


def scan_metadata_directory(path: str | Path) -> tuple[MetadataRecord, ...]: ...
