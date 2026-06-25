from rm2_backup.runner import PipelineResult


def test_pipeline_result_tracks_published_count() -> None:
    result = PipelineResult(planned=3, completed=2, skipped=0, failed=1, published=2)

    assert result.planned == 3
    assert result.completed == 2
    assert result.failed == 1
    assert result.published == 2
