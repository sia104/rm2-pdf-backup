from pathlib import Path
from pathlib import PurePosixPath

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

    assert result == (svg,)


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
