"""Template background composition helpers."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rm2_backup.templates import DocumentTemplateSummary, TemplateFile, TemplateInventory

SVG_NS = "http://www.w3.org/2000/svg"


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
    """Resolve the first detectable template reference to a copied template file.

    Missing or ambiguous template references are reported as warnings. They do not
    represent render failures because handwriting-only output is still publishable.
    """

    if not summary.references:
        return TemplateResolution(template=None, warning="template reference not detected")
    if summary.missing:
        return TemplateResolution(
            template=None,
            warning=f"template missing: {','.join(summary.missing)}",
        )
    reference = summary.references[0]
    matches = tuple(file for file in inventory.files if file.stem == reference)
    if not matches:
        return TemplateResolution(template=None, warning=f"template not found: {reference}")
    preferred = _prefer_vector_template(matches)
    return TemplateResolution(template=preferred)


def compose_svg_template_background(
    *,
    template_svg: Path,
    handwriting_svg: Path,
    output_svg: Path,
) -> Path:
    """Write an SVG with the template behind the handwriting.

    This helper is deliberately limited to SVG backgrounds. Non-SVG template
    formats should be converted before this step or handled by a separate image
    composition path.
    """

    template_tree = ET.parse(template_svg)
    handwriting_tree = ET.parse(handwriting_svg)
    template_root = template_tree.getroot()
    handwriting_root = handwriting_tree.getroot()

    if not _is_svg(template_root):
        raise ValueError(f"Template is not an SVG: {template_svg}")
    if not _is_svg(handwriting_root):
        raise ValueError(f"Handwriting render is not an SVG: {handwriting_svg}")

    output_root = copy.deepcopy(handwriting_root)
    output_root[:] = []
    output_root.set("data-rm2-template-source", str(template_svg))

    for attr in ("viewBox", "width", "height"):
        if attr in template_root.attrib:
            output_root.set(attr, template_root.attrib[attr])

    template_group = ET.Element(f"{{{SVG_NS}}}g", {"id": "rm2-template-background"})
    handwriting_group = ET.Element(f"{{{SVG_NS}}}g", {"id": "rm2-handwriting"})

    for child in list(template_root):
        template_group.append(copy.deepcopy(child))
    for child in list(handwriting_root):
        handwriting_group.append(copy.deepcopy(child))

    output_root.append(template_group)
    output_root.append(handwriting_group)
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    ET.register_namespace("", SVG_NS)
    ET.ElementTree(output_root).write(output_svg, encoding="utf-8", xml_declaration=True)
    return output_svg


def _prefer_vector_template(matches: tuple[TemplateFile, ...]) -> TemplateFile:
    for file in matches:
        if file.suffix.lower() == ".svg":
            return file
    return matches[0]


def _is_svg(element: ET.Element) -> bool:
    return element.tag.endswith("svg")
