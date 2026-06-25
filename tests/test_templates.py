import json

from rm2_backup.templates import build_template_inventory, template_provenance_for_document


def test_template_inventory_includes_custom_files_and_templates_json_aliases(tmp_path):
    templates = tmp_path / "raw" / "current" / "templates"
    templates.mkdir(parents=True)
    (templates / "DIAD_Form.svg").write_text("<svg />", encoding="utf-8")
    (templates / "templates.json").write_text(
        json.dumps({"templates": [{"name": "DIAD Form", "filename": "DIAD_Form"}]}),
        encoding="utf-8",
    )

    inventory = build_template_inventory(tmp_path / "raw" / "current")

    assert inventory.file_count == 2
    assert inventory.has_templates_json is True
    assert "diad_form" in inventory.aliases
    assert "diad form" in inventory.aliases


def test_template_provenance_reports_referenced_and_missing_templates(tmp_path):
    raw_current = tmp_path / "raw" / "current"
    raw_xochitl = raw_current / "xochitl"
    templates = raw_current / "templates"
    raw_xochitl.mkdir(parents=True)
    templates.mkdir(parents=True)
    (templates / "Known_Template.svg").write_text("<svg />", encoding="utf-8")
    (raw_xochitl / "doc.content").write_text(
        json.dumps(
            {
                "cPages": {
                    "pages": [
                        {"id": "page1", "template": {"value": "Known_Template"}},
                        {"id": "page2", "template": {"value": "Missing_Template"}},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    provenance = template_provenance_for_document(
        raw_xochitl=raw_xochitl,
        raw_current=raw_current,
        uuid="doc",
    )

    assert provenance.referenced == ("Known_Template", "Missing_Template")
    assert provenance.missing == ("Missing_Template",)
    assert "Missing_Template" in provenance.warning
