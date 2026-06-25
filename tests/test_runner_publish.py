from rm2_backup.runner import PipelineEvent, PipelineResult, _write_run_report
from rm2_backup.templates import TemplateProvenance


def test_pipeline_result_tracks_published_count() -> None:
    result = PipelineResult(planned=3, completed=2, skipped=0, failed=1, published=2)

    assert result.planned == 3
    assert result.completed == 2
    assert result.failed == 1
    assert result.published == 2


def test_write_run_report_contains_counts_and_events(tmp_path) -> None:
    report = _write_run_report(
        tmp_path / "reports" / "run-local-report.txt",
        planned=2,
        completed=1,
        skipped=0,
        failed=1,
        published=1,
        events=[
            PipelineEvent(
                uuid="ok-doc",
                visible_path=("Folder", "Notebook"),
                output_relative_path="Folder/Notebook.pdf",
                status="ok",
                template_provenance=TemplateProvenance(
                    referenced=("DIAD_Form",),
                    missing=(),
                    file_count=3,
                    has_templates_json=True,
                ),
            ),
            PipelineEvent(
                uuid="bad-doc",
                visible_path=("Broken",),
                output_relative_path="Broken.pdf",
                status="failed",
                message="renderer error with detail",
            ),
        ],
    )

    text = report.read_text(encoding="utf-8")
    assert "planned: 2" in text
    assert "published: 1" in text
    assert "- ok: Folder/Notebook" in text
    assert "- failed: Broken" in text
    assert "templates: files=3 templates_json=True referenced=1 missing=0" in text
    assert "template_references: DIAD_Form" in text
    assert "message: renderer error with detail" in text
