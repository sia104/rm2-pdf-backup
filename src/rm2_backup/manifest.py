"""SQLite manifest and change detection."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from rm2_backup.render_queue import RenderPlanItem


@dataclass(frozen=True, slots=True)
class ManifestDecision:
    """Change-detection decision for a planned render item."""

    uuid: str
    should_render: bool
    reason: str


class Manifest:
    """Small SQLite-backed manifest for render status."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self._init_schema()

    def close(self) -> None:
        """Close the database connection."""

        self.connection.close()

    def __enter__(self) -> Manifest:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def decide(self, item: RenderPlanItem, source_hash: str) -> ManifestDecision:
        """Return whether a planned item needs rendering."""

        row = self.connection.execute(
            "select source_hash, output_relative_path, render_status from documents where uuid = ?",
            (item.uuid,),
        ).fetchone()
        output_path = str(item.output_relative_path)
        if row is None:
            return ManifestDecision(item.uuid, True, "new document")
        previous_hash, previous_output, status = row
        if previous_hash != source_hash:
            return ManifestDecision(item.uuid, True, "source changed")
        if previous_output != output_path:
            return ManifestDecision(item.uuid, True, "output path changed")
        if status != "ok":
            return ManifestDecision(item.uuid, True, "previous render not ok")
        return ManifestDecision(item.uuid, False, "unchanged")

    def record_render_result(
        self,
        item: RenderPlanItem,
        *,
        source_hash: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Record the latest render status for a document."""

        self.connection.execute(
            """
            insert into documents(uuid, source_hash, output_relative_path, render_status, error)
            values (?, ?, ?, ?, ?)
            on conflict(uuid) do update set
                source_hash = excluded.source_hash,
                output_relative_path = excluded.output_relative_path,
                render_status = excluded.render_status,
                error = excluded.error,
                updated_at = current_timestamp
            """,
            (item.uuid, source_hash, str(item.output_relative_path), status, error),
        )
        self.connection.commit()

    def _init_schema(self) -> None:
        self.connection.execute(
            """
            create table if not exists documents(
                uuid text primary key,
                source_hash text not null,
                output_relative_path text not null,
                render_status text not null,
                error text,
                updated_at text not null default current_timestamp
            )
            """
        )
        self.connection.commit()


def hash_document_source(raw_xochitl: Path, uuid: str) -> str:
    """Hash raw source files belonging to a document UUID.

    The hash is deterministic and tolerant of missing optional files. It is used
    for change detection, not for cryptographic integrity guarantees.
    """

    hasher = hashlib.sha256()
    for path in sorted(raw_xochitl.glob(f"{uuid}*")):
        if not path.is_file():
            continue
        hasher.update(path.name.encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def output_path_text(path: PurePosixPath) -> str:
    """Return a stable text representation for manifest output paths."""

    return str(path)
