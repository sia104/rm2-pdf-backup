from pathlib import Path
from pathlib import PurePosixPath
import subprocess

from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.rmc_svg_template import TemplateRmcSvgRenderer
from rm2_backup.renderers.rmc_svg_template import add_template_backgrounds


def _item(uuid: str = "doc") -> RenderPlanItem:
    return RenderPlanItem(
        uuid=uuid,
        visible_name="Notebook",
        visible_path=("Notebook",),
        output_relative_path=PurePosixPath("Notebook.pdf"),
    )


def test_add_template_backgrounds_returns_original_when_no_template(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "xochitl"
    raw.mkdir(parents=True)
    svg = tmp_path / "page.svg"
    svg.write_text("", encoding="utf-8")

    result = add_template_backgrounds(
        raw_xochitl=raw,
        uuid="doc",
        svg_paths=(svg,),
        work_dir=tmp_path / "work",
    )

    assert result.svg_paths == (svg,)
    assert result.warning is None


def test_template_renderer_reports_missing_rmc_executable_category(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "xochitl"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm")

    def fake_runner(argv, **kwargs):
        raise FileNotFoundError("rmc")

    renderer = TemplateRmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert not result.ok
    assert result.output_path is None
    assert result.error is not None
    assert "category=renderer_executable_not_found" in result.error


def test_add_template_backgrounds_reports_png_background(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "xochitl"
    templates = tmp_path / "raw" / "templates"
    raw.mkdir(parents=True)
    templates.mkdir(parents=True)
    (templates / "Form.png").write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (raw / "doc.content").write_text('{"template": "Form"}', encoding="utf-8")
    svg = tmp_path / "page.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path id="ink" d="M 1 1 L 9 9" /></svg>',
        encoding="utf-8",
    )

    result = add_template_backgrounds(
        raw_xochitl=raw,
        uuid="doc",
        svg_paths=(svg,),
        work_dir=tmp_path / "work",
    )

    assert result.warning == "template_background=png"
    assert len(result.svg_paths) == 1
    assert result.svg_paths[0].read_text(encoding="utf-8").count("data:image/png;base64,") == 1


def test_template_renderer_reports_template_background_diagnostics(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw" / "xochitl"
    templates = tmp_path / "raw" / "templates"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    templates.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm")
    (raw / "doc.content").write_text('{"template": "Form"}', encoding="utf-8")
    (templates / "Form.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect id="paper" width="100" height="100" /></svg>',
        encoding="utf-8",
    )

    def fake_runner(argv, **kwargs):
        svg_path = Path(argv[4])
        svg_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path id="ink" d="M 1 1 L 9 9" /></svg>',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    def fake_compose(svg_paths, output_pdf):
        assert len(svg_paths) == 1
        output_pdf.write_bytes(b"%PDF-template\n%%EOF\n")
        return output_pdf

    monkeypatch.setattr(
        "rm2_backup.renderers.rmc_svg_template.compose_svg_pages_to_pdf",
        fake_compose,
    )

    renderer = TemplateRmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert result.ok
    assert result.warning == "template_background=svg"
    assert result.diagnostics.renderer_primary == "rmc-svg"
    assert result.diagnostics.renderer_final == "rmc-svg"
    assert result.diagnostics.template_background == "svg"
    assert result.diagnostics.highlighter_colour_mode == "unknown"
