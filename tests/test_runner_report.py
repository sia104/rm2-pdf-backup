from pathlib import Path


def test_placeholder_for_run_local_reporting_suite(tmp_path: Path) -> None:
    assert tmp_path.exists()
