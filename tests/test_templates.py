import json

from rm2_backup.templates import build_template_inventory, summarise_document_templates


def test_template_inventory_hashes_copied_files(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "DIAD-form.svg").write_text("<svg />", encoding="utf-8")

    inventory = build_template_inventory(templates)

    assert inventory.count == 1
    assert inventory.files[0].relative_path == "DIAD-form.svg"
    assert inventory.files[0].stem == "DIAD-form"
    assert len(inventory.files[0].sha256) == 64


def test_document_template_summary_detects_found_template(tmp_path):
    xochitl = tmp_path / "xochitl"
    xochitl.mkdir()
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "DIAD-form.svg").write_text("<svg />", encoding="utf-8")
    (xochitl / "doc.content").write_text(
        json.dumps({"cPages": {"pages": [{"template": {"name": "DIAD-form"}}]}}),
        encoding="utf-8",
    )

    summary = summarise_document_templates(
        raw_xochitl=xochitl,
        uuid="doc",
        inventory=build_template_inventory(templates),
    )

    assert summary.references == ("DIAD-form",)
    assert summary.missing == ()
    assert summary.ok


def test_document_template_summary_warns_about_missing_template(tmp_path):
    xochitl = tmp_path / "xochitl"
    xochitl.mkdir()
    templates = tmp_path / "templates"
    templates.mkdir()
    (xochitl / "doc.content").write_text(
        json.dumps({"template": "Missing-form"}),
        encoding="utf-8",
    )

    summary = summarise_document_templates(
        raw_xochitl=xochitl,
        uuid="doc",
        inventory=build_template_inventory(templates),
    )

    assert summary.references == ("Missing-form",)
    assert summary.missing == ("Missing-form",)
    assert not summary.ok
    assert "template_missing=Missing-form" in summary.message
