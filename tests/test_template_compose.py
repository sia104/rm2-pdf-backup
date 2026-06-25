import xml.etree.ElementTree as ET

from rm2_backup.template_compose import compose_svg_template_background, resolve_template_file
from rm2_backup.templates import DocumentTemplateSummary, TemplateFile, TemplateInventory


def test_resolve_template_file_prefers_svg(tmp_path):
    inventory = TemplateInventory(
        root=tmp_path,
        files=(
            TemplateFile("Form.png", "Form", ".png", "0" * 64),
            TemplateFile("Form.svg", "Form", ".svg", "1" * 64),
        ),
    )
    summary = DocumentTemplateSummary(references=("Form",), missing=())

    resolution = resolve_template_file(summary, inventory)

    assert resolution.ok
    assert resolution.template is not None
    assert resolution.template.relative_path == "Form.svg"
    assert resolution.warning is None


def test_resolve_template_file_warns_for_missing_template(tmp_path):
    inventory = TemplateInventory(root=tmp_path, files=())
    summary = DocumentTemplateSummary(references=("Missing",), missing=("Missing",))

    resolution = resolve_template_file(summary, inventory)

    assert not resolution.ok
    assert resolution.template is None
    assert resolution.warning == "template missing: Missing"


def test_compose_svg_template_background_places_template_first(tmp_path):
    template_svg = tmp_path / "template.svg"
    handwriting_svg = tmp_path / "handwriting.svg"
    output_svg = tmp_path / "combined.svg"
    template_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect id="paper" width="100" height="100" /></svg>',
        encoding="utf-8",
    )
    handwriting_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path id="ink" d="M 1 1 L 9 9" /></svg>',
        encoding="utf-8",
    )

    compose_svg_template_background(
        template_svg=template_svg,
        handwriting_svg=handwriting_svg,
        output_svg=output_svg,
    )

    root = ET.parse(output_svg).getroot()
    children = list(root)
    assert children[0].attrib["id"] == "rm2-template-background"
    assert children[1].attrib["id"] == "rm2-handwriting"
    assert children[0][0].attrib["id"] == "paper"
    assert children[1][0].attrib["id"] == "ink"
