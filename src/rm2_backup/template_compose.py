"""Template background composition helpers."""

from __future__ import annotations

import base64
import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rm2_backup.templates import (
    DocumentTemplateSummary,
    TemplateFile,
    TemplateInventory,
    TemplateManifestEntry,
)

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"


@dataclass(frozen=True, slots=True)
class TemplateResolution:
    """Resolved background template for a document or page."""

    template: TemplateFile | None
    warning: str | None = None

    @property
    def ok(self) -> bool:
        return self.template is not None


def resolve_template_file(
    summary: DocumentTemplateSummary,
    inventory: TemplateInventory,
) -> TemplateResolution:
    """Resolve the first detectable template reference to a copied template file."""

    if not summary.references:
        return TemplateResolution(template=None, warning="template reference not detected")
    if summary.missing:
        return TemplateResolution(
            template=None,
            warning=f"template missing: {','.join(summary.missing)}",
        )

    reference = summary.references[0]
    manifest_entry = _find_manifest_entry(reference, inventory.manifest_entries)
    if manifest_entry is None:
        matches = tuple(file for file in inventory.files if file.stem == reference)
    else:
        matches = tuple(file for file in inventory.files if file.stem == manifest_entry.filename_stem)
    if not matches:
        return TemplateResolution(template=None, warning=f"template not found: {reference}")
    return TemplateResolution(template=_prefer_vector_template(matches))


def compose_svg_template_background(
    *,
    template_svg: Path,
    handwriting_svg: Path,
    output_svg: Path,
) -> Path:
    """Backward-compatible wrapper for SVG template composition."""

    return compose_template_background(
        template_asset=template_svg,
        handwriting_svg=handwriting_svg,
        output_svg=output_svg,
    )


def compose_template_background(
    *,
    template_asset: Path,
    handwriting_svg: Path,
    output_svg: Path,
) -> Path:
    """Write an SVG with an SVG or PNG template behind the handwriting."""

    handwriting_tree = ET.parse(handwriting_svg)
    handwriting_root = handwriting_tree.getroot()
    if not _is_svg(handwriting_root):
        raise ValueError(f"Handwriting render is not an SVG: {handwriting_svg}")

    output_root = copy.deepcopy(handwriting_root)
    output_root[:] = []
    output_root.set("data-rm2-template-source", str(template_asset))

    template_group = ET.Element(f"{{{SVG_NS}}}g", {"id": "rm2-template-background"})
    handwriting_group = ET.Element(f"{{{SVG_NS}}}g", {"id": "rm2-handwriting"})

    _append_template_background(output_root, template_group, template_asset)
    for child in list(handwriting_root):
        handwriting_group.append(copy.deepcopy(child))

    output_root.append(template_group)
    output_root.append(handwriting_group)
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    ET.ElementTree(output_root).write(output_svg, encoding="utf-8", xml_declaration=True)
    return output_svg


def _prefer_vector_template(matches: tuple[TemplateFile, ...]) -> TemplateFile:
    for file in matches:
        if file.suffix.lower() == ".svg":
            return file
    return matches[0]


def _is_svg(element: ET.Element) -> bool:
    return element.tag.endswith("svg")


def _find_manifest_entry(
    reference: str,
    manifest_entries: tuple[TemplateManifestEntry, ...],
) -> TemplateManifestEntry | None:
    for entry in manifest_entries:
        if reference in entry.aliases:
            return entry
    return None


def _append_template_background(
    output_root: ET.Element,
    template_group: ET.Element,
    template_asset: Path,
) -> None:
    if template_asset.suffix.lower() == ".svg":
        template_tree = ET.parse(template_asset)
        template_root = template_tree.getroot()
        if not _is_svg(template_root):
            raise ValueError(f"Template is not an SVG: {template_asset}")
        for attr in ("viewBox", "width", "height"):
            if attr in template_root.attrib:
                output_root.set(attr, template_root.attrib[attr])
        for child in list(template_root):
            template_group.append(copy.deepcopy(child))
        return

    if template_asset.suffix.lower() != ".png":
        raise ValueError(f"Unsupported template asset: {template_asset}")

    image = ET.Element(
        f"{{{SVG_NS}}}image",
        {
            "x": "0",
            "y": "0",
            "width": "100%",
            "height": "100%",
            "preserveAspectRatio": "none",
            f"{{{XLINK_NS}}}href": _png_data_uri(template_asset),
        },
    )
    template_group.append(image)


def _png_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
