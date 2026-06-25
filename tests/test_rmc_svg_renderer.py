from pathlib import Path, PurePosixPath
import subprocess

from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.rmc_svg import RmcSvgRenderer, find_rm_page_files


def _item(uuid: str = "doc") -> RenderPlanItem:
    return RenderPlanItem(
        uuid=uuid,
        visible_name="Notebook",
        visible_path=("Notebook",),
        output_relative_path=PurePosixPath("Notebook.pdf"),
    )


def test_find_rm_page_files_uses_content_order(tmp_path: Path) -> None:
    raw = tmp_path
    doc_dir = raw / "doc"
    doc_dir.mkdir()
    (raw / "doc.content").write_text('{"pages": ["b", "a"]}', encoding="utf-8")
    page_a = doc_dir / "a.rm"
    page_b = doc_dir / "b.rm"
    page_a.write_bytes(b"a")
    page_b.write_bytes(b"b")

    assert find_rm_page_files(raw, "doc") == (page_b, page_a)


def test_render_svg_pages_accepts_well_formed_svg_with_nonzero_exit(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    page = doc_dir / "page.rm"
    page.write_bytes(b"rm")

    def fake_runner(argv, **kwargs):
        svg_path = Path(argv[4])
        svg_path.write_text("<svg></svg>", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="KeyError: 9")

    renderer = RmcSvgRenderer(runner=fake_runner)
    summary = renderer.render_svg_pages(_item(), raw_xochitl=raw, work_dir=tmp_path / "svg")

    assert summary.total_pages == 1
    assert summary.non_empty_pages == 1
    assert summary.usable_pages == 1
    assert summary.malformed_pages == 0
    assert summary.clean_pages == 0
    assert summary.ok_for_composition


def test_render_svg_pages_rejects_truncated_svg(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    page = doc_dir / "page.rm"
    page.write_bytes(b"rm")

    def fake_runner(argv, **kwargs):
        svg_path = Path(argv[4])
        svg_path.write_text("<svg>", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="KeyError: 9")

    renderer = RmcSvgRenderer(runner=fake_runner)
    summary = renderer.render_svg_pages(_item(), raw_xochitl=raw, work_dir=tmp_path / "svg")

    assert summary.total_pages == 1
    assert summary.non_empty_pages == 1
    assert summary.usable_pages == 0
    assert summary.malformed_pages == 1
    assert not summary.ok_for_composition


def test_render_reports_pdf_composition_failure_after_svg_success(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm")

    def fake_runner(argv, **kwargs):
        svg_path = Path(argv[4])
        svg_path.write_text("<svg></svg>", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    renderer = RmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert not result.ok
    assert result.output_path is None
    assert result.error is not None
    assert "PDF" in result.error
