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


def test_render_reports_no_rm_pages_category(tmp_path: Path) -> None:
    renderer = RmcSvgRenderer()

    result = renderer.render(_item(), raw_xochitl=tmp_path / "raw", staging_pdf=tmp_path / "out.pdf")

    assert not result.ok
    assert result.output_path is None
    assert result.error is not None
    assert "category=no_rm_pages" in result.error


def test_render_reports_malformed_svg_category(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm-page-bytes")

    def fake_runner(argv, **kwargs):
        if "-t" not in argv:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="direct pdf failed")
        svg_path = Path(argv[4])
        svg_path.write_text("<svg>", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="KeyError: 9\npalette fail")

    renderer = RmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert not result.ok
    assert result.output_path is None
    assert result.error is not None
    assert "category=malformed_svg" in result.error
    assert "page=page.rm" in result.error
    assert "page_bytes=13" in result.error
    assert "svg=0001-page.svg" in result.error
    assert "svg_bytes=5" in result.error
    assert "return_code=1" in result.error
    assert "parse_error=no element found" in result.error
    assert "stderr=KeyError: 9 palette fail" in result.error
    assert "fallback_error=" in result.error


def test_render_uses_direct_pdf_fallback_after_malformed_svg(tmp_path: Path, monkeypatch) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm-page-bytes")
    calls: list[tuple[str, ...]] = []

    def fake_runner(argv, **kwargs):
        calls.append(tuple(str(part) for part in argv))
        if "-t" in argv:
            svg_path = Path(argv[4])
            svg_path.write_text("<svg>", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="KeyError: 9")
        page_pdf = Path(argv[3])
        page_pdf.write_bytes(b"%PDF-page\n%%EOF\n")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    def fake_compose_pdf_pages(page_pdfs, output_pdf):
        assert len(page_pdfs) == 1
        assert page_pdfs[0].name == "0001-page.pdf"
        output_pdf.write_bytes(b"%PDF-fallback\n%%EOF\n")
        return output_pdf

    monkeypatch.setattr(
        "rm2_backup.renderers.rmc_svg.compose_pdf_pages_to_pdf",
        fake_compose_pdf_pages,
    )

    renderer = RmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert result.ok
    assert result.output_path == tmp_path / "out.pdf"
    assert result.warning is not None
    assert result.diagnostics.renderer_primary == "rmc-svg"
    assert result.diagnostics.renderer_final == "rmc-pdf-fallback"
    assert result.diagnostics.highlighter_colour_mode == "unknown"
    assert result.diagnostics.fallback_attempted
    assert result.diagnostics.fallback_reason == "malformed_svg"
    assert "renderer_warning=used_direct_pdf_fallback_after_svg_failure" in result.warning
    assert "category=malformed_svg" in result.warning
    assert calls[0][0:3] == ("rmc", "-t", "svg")
    assert calls[1][0] == "rmc"
    assert calls[1][1].endswith("page.rm")
    assert calls[1][2] == "-o"


def test_render_reports_no_svg_output_category(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm")

    def fake_runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unsupported")

    renderer = RmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert not result.ok
    assert result.output_path is None
    assert result.error is not None
    assert "category=no_svg_output" in result.error


def test_render_reports_missing_rmc_executable_category(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    doc_dir = raw / "doc"
    doc_dir.mkdir(parents=True)
    (doc_dir / "page.rm").write_bytes(b"rm")

    def fake_runner(argv, **kwargs):
        raise FileNotFoundError("rmc")

    renderer = RmcSvgRenderer(runner=fake_runner)
    result = renderer.render(_item(), raw_xochitl=raw, staging_pdf=tmp_path / "out.pdf")

    assert not result.ok
    assert result.output_path is None
    assert result.error is not None
    assert "category=renderer_executable_not_found" in result.error
    assert "usable=0/1" in result.error
    assert "page=page.rm" in result.error
    assert "return_code=127" in result.error
    assert "stderr=renderer executable not found: rmc" in result.error


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
