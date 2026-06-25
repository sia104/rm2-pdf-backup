"""Template provenance helpers for copied reMarkable data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TemplateFile:
    """One copied template-related file."""

    relative_path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class TemplateInventory:
    """Inventory of copied standard and custom templates."""

    root: Path
    files: tuple[TemplateFile, ...]
    aliases: frozenset[str]
    has_templates_json: bool

    @property
    def file_count(self) -> int:
        return len(self.files)


@dataclass(frozen=True, slots=True)
class TemplateProvenance:
    """Template information relevant to one document render."""

    referenced: tuple[str, ...]
    missing: tuple[str, ...]
    file_count: int
    has_templates_json: bool

    @property
    def warning(self) -> str | None:
        if self.missing:
            return "template warning: missing referenced template(s): " + ", ".join(
                self.missing
            )
        if self.referenced:
            return "template provenance: referenced template(s): " + ", ".join(
                self.referenced
            )
        return None


def build_template_inventory(raw_current: Path) -> TemplateInventory:
    """Build a stable inventory from ``raw/current/templates``.

    The inventory records file hashes for provenance and builds a permissive alias
    set from file names and ``templates.json`` entries. This supports standard and
    custom templates without assuming a fixed reMarkable schema.
    """

    root = raw_current / "templates"
    files: list[TemplateFile] = []
    aliases: set[str] = set()
    has_templates_json = False

    if not root.is_dir():
        return TemplateInventory(root=root, files=(), aliases=frozenset(), has_templates_json=False)

    for path in sorted(file for file in root.rglob("*") if file.is_file()):
        relative = path.relative_to(root).as_posix()
        files.append(TemplateFile(relative_path=relative, sha256=_sha256(path)))
        aliases.update(_aliases_from_path(path))
        if path.name == "templates.json":
            has_templates_json = True
            aliases.update(_aliases_from_templates_json(path))

    return TemplateInventory(
        root=root,
        files=tuple(files),
        aliases=frozenset(alias for alias in aliases if alias),
        has_templates_json=has_templates_json,
    )


def template_provenance_for_document(
    *,
    raw_xochitl: Path,
    raw_current: Path,
    uuid: str,
) -> TemplateProvenance:
    """Return referenced/missing template information for a document."""

    inventory = build_template_inventory(raw_current)
    references = _referenced_templates(raw_xochitl, uuid)
    missing = tuple(
        reference
        for reference in references
        if _normalise_alias(reference) not in inventory.aliases
    )
    return TemplateProvenance(
        referenced=references,
        missing=missing,
        file_count=inventory.file_count,
        has_templates_json=inventory.has_templates_json,
    )


def _referenced_templates(raw_xochitl: Path, uuid: str) -> tuple[str, ...]:
    content_path = raw_xochitl / f"{uuid}.content"
    if not content_path.exists():
        return ()
    try:
        payload = json.loads(content_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()

    references = sorted({_normalise_display(value) for value in _template_values(payload)})
    return tuple(value for value in references if value)


def _template_values(value: Any, *, parent_key: str | None = None) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lower_key = str(key).lower()
            if "template" in lower_key:
                found.extend(_strings_inside(item))
            else:
                found.extend(_template_values(item, parent_key=lower_key))
    elif isinstance(value, list):
        for item in value:
            found.extend(_template_values(item, parent_key=parent_key))
    return found


def _strings_inside(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_strings_inside(item))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_strings_inside(item))
        return strings
    return []


def _aliases_from_path(path: Path) -> set[str]:
    aliases = {_normalise_alias(path.name), _normalise_alias(path.stem)}
    if path.suffix:
        aliases.add(_normalise_alias(path.name.removesuffix(path.suffix)))
    return aliases


def _aliases_from_templates_json(path: Path) -> set[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {_normalise_alias(value) for value in _strings_inside(payload) if value}


def _normalise_alias(value: str) -> str:
    value = value.strip().lower()
    for suffix in (".svg", ".png", ".jpg", ".jpeg"):
        value = value.removesuffix(suffix)
    return value


def _normalise_display(value: str) -> str:
    return value.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
