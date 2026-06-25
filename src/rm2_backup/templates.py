"""Template provenance helpers.

This module deliberately records template provenance without making template files part
of the document source hash. That preserves historical rendered PDFs: a later template
change does not silently regenerate older successful exports.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TemplateFile:
    """One copied template-side file."""

    relative_path: str
    stem: str
    suffix: str
    sha256: str


@dataclass(frozen=True, slots=True)
class TemplateInventory:
    """Copied template inventory."""

    root: Path
    files: tuple[TemplateFile, ...]

    @property
    def stems(self) -> frozenset[str]:
        return frozenset(file.stem for file in self.files)

    @property
    def count(self) -> int:
        return len(self.files)


@dataclass(frozen=True, slots=True)
class DocumentTemplateSummary:
    """Template references found for a document."""

    references: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing

    @property
    def message(self) -> str:
        if not self.references:
            return "template_refs=none"
        refs = ",".join(self.references)
        if self.missing:
            return f"template_refs={refs} template_missing={','.join(self.missing)}"
        return f"template_refs={refs} template_status=found"


def build_template_inventory(root: Path) -> TemplateInventory:
    """Hash copied template files under ``root``.

    Missing template directories are represented as an empty inventory so template
    absence can be reported as a warning rather than a render failure.
    """

    if not root.exists():
        return TemplateInventory(root=root, files=())
    files: list[TemplateFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            TemplateFile(
                relative_path=path.relative_to(root).as_posix(),
                stem=path.stem,
                suffix=path.suffix,
                sha256=_sha256_file(path),
            )
        )
    return TemplateInventory(root=root, files=tuple(files))


def summarise_document_templates(
    *,
    raw_xochitl: Path,
    uuid: str,
    inventory: TemplateInventory,
) -> DocumentTemplateSummary:
    """Return template references for a document, if detectable.

    reMarkable content JSON has changed across software versions. Rather than
    assuming one schema, this scans JSON values under keys containing
    ``template`` and records string values. Unknown or missing content files are
    treated as no detectable references.
    """

    references = _document_template_references(raw_xochitl / f"{uuid}.content")
    missing = tuple(ref for ref in references if ref not in inventory.stems)
    return DocumentTemplateSummary(references=references, missing=missing)


def _document_template_references(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    refs: set[str] = set()
    _collect_template_refs(payload, refs=refs)
    return tuple(sorted(refs))


def _collect_template_refs(value: Any, *, refs: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if "template" in key_text:
                _collect_template_value(item, refs=refs)
            else:
                _collect_template_refs(item, refs=refs)
    elif isinstance(value, list):
        for item in value:
            _collect_template_refs(item, refs=refs)


def _collect_template_value(value: Any, *, refs: set[str]) -> None:
    if isinstance(value, str) and value.strip():
        refs.add(value.strip())
    elif isinstance(value, dict):
        for item in value.values():
            _collect_template_value(item, refs=refs)
    elif isinstance(value, list):
        for item in value:
            _collect_template_value(item, refs=refs)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
