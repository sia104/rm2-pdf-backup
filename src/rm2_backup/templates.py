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

_TEMPLATE_VALUE_KEYS = {"name", "value", "filename", "file", "template", "templateName"}
_MANIFEST_ALIAS_KEYS = ("filename", "name", "iconCode", "template", "value")


@dataclass(frozen=True, slots=True)
class TemplateFile:
    """One copied template-side file."""

    relative_path: str
    stem: str
    suffix: str
    sha256: str


@dataclass(frozen=True, slots=True)
class TemplateManifestEntry:
    """One template entry from copied ``templates.json``."""

    filename_stem: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TemplateInventory:
    """Copied template inventory."""

    root: Path
    files: tuple[TemplateFile, ...]
    manifest_entries: tuple[TemplateManifestEntry, ...] = ()

    @property
    def stems(self) -> frozenset[str]:
        return frozenset(file.stem for file in self.files)

    @property
    def count(self) -> int:
        return len(self.files)

    @property
    def known_references(self) -> frozenset[str]:
        refs = set(self.stems)
        for entry in self.manifest_entries:
            refs.update(entry.aliases)
        return frozenset(refs)


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
    """Hash copied template files under ``root``."""

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
    return TemplateInventory(
        root=root,
        files=tuple(files),
        manifest_entries=_load_template_manifest_entries(root / "templates.json"),
    )


def summarise_document_templates(
    *,
    raw_xochitl: Path,
    uuid: str,
    inventory: TemplateInventory,
) -> DocumentTemplateSummary:
    """Return template references for a document, if detectable."""

    references = _document_template_references(raw_xochitl / f"{uuid}.content")
    missing = tuple(ref for ref in references if ref not in inventory.known_references)
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
            key_text = str(key)
            if "template" in key_text.lower():
                _collect_template_node(item, refs=refs)
            else:
                _collect_template_refs(item, refs=refs)
    elif isinstance(value, list):
        for item in value:
            _collect_template_refs(item, refs=refs)


def _collect_template_node(value: Any, *, refs: set[str]) -> None:
    if isinstance(value, str):
        _add_template_ref(value, refs=refs)
        return
    if isinstance(value, list):
        for item in value:
            _collect_template_node(item, refs=refs)
        return
    if not isinstance(value, dict):
        return

    for key, item in value.items():
        key_text = str(key)
        if key_text in _TEMPLATE_VALUE_KEYS and isinstance(item, str):
            _add_template_ref(item, refs=refs)
        elif "template" in key_text.lower():
            _collect_template_node(item, refs=refs)


def _add_template_ref(value: str, *, refs: set[str]) -> None:
    cleaned = value.strip()
    if not cleaned:
        return
    if ":" in cleaned and cleaned.replace(":", "").isdigit():
        return
    refs.add(Path(cleaned).stem)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_template_manifest_entries(path: Path) -> tuple[TemplateManifestEntry, ...]:
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()

    if isinstance(payload, dict):
        raw_entries = payload.get("templates", ())
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raw_entries = ()

    entries: list[TemplateManifestEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        filename = _manifest_string(item.get("filename"))
        if filename is None:
            continue
        aliases = {Path(filename).stem}
        for key in _MANIFEST_ALIAS_KEYS:
            value = _manifest_string(item.get(key))
            if value is not None:
                aliases.add(Path(value).stem)
        entries.append(
            TemplateManifestEntry(
                filename_stem=Path(filename).stem,
                aliases=tuple(sorted(aliases)),
            )
        )
    return tuple(entries)


def _manifest_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned
