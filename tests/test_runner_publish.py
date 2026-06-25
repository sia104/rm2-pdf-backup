from pathlib import Path

from rm2_backup.config import AppConfig, PathsConfig, RendererConfig, Rm2Config
from rm2_backup.renderers.rmc_svg import RmcSvgRenderer
from rm2_backup.renderers.rmc_svg_template import TemplateRmcSvgRenderer
from rm2_backup.runner import PipelineEvent, PipelineResult, _renderer_from_config, _write_run_report


def test_pipeline_result_tracks_published_count() -> None:
    result = PipelineResult(planned=3, completed=2, skipped=0, failed=1, published=2)

    assert result.planned == 3
    assert result.completed == 2
    assert result.failed == 1
    assert result.published == 2


def test_renderer_selection_uses_normal_rmc_svg_by_default() -> None:
    renderer = _renderer_from_config(_app_config(RendererConfig(mode="rmc-svg")))

    assert isinstance(renderer, RmcSvgRenderer)
    assert not isinstance(renderer, TemplateRmcSvgRenderer)


def test_renderer_selection_uses_template_rmc_svg_when_enabled() -> None:
    renderer = _renderer_from_config(RendererConfig(mode="rmc-svg", include_templates=True) | None)  # type: ignore[operator]

    assert renderer is not None


def test_write_run_report_contains_counts_and_events(tmp_path) -> None:
    report = _write_run_report(
        tmp_path / "reports" / "run-local-report.txt",
        planned=2,
        completed=1,
        skipped=0,
        failed=1,
        published=1,
        template_count=66,
        events=[
            PipelineEvent(
                uuid="ok-doc",
                visible_path=("Folder", "Notebook"),
                output_relative_path="Folder/Notebook.pdf",
                status="ok",
            ),
            PipelineEvent(
                uuid="bad-doc",
                visible_path=("Broken",),
                output_relative_path="Broken.pdf",
                status="failed",
                message="renderer error\nwith detail",
            ),
        ],
    )

    text = report.read_text(encoding="utf-8")
    assert "planned: 2" in text
    assert "published: 1" in text
    assert "templates_file_count: 66" in text
    assert "- ok: Folder/Notebook" in text
    assert "- failed: Broken" in text
    assert "message: renderer error with detail" in text


def _app_config(renderer: RendererConfig) -> AppConfig:
    root = Path("/tmp/rm2-test")
    return AppConfig(
        rm2=Rm2Config(host="rm2"),
        paths=PathsConfig(
            backup_root=root,
            raw_current=root / "raw",
            pdf_current=root / "pdf",
            staging=root / "staging",
            database=root / "db.sqlite",
            reports=root / "reports",
            logs=root / "logs",
        ),
        renderer=renderer,
    )
