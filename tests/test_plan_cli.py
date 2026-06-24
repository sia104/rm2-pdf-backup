from pathlib import Path

from rm2_backup.cli import main

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "synthetic_xochitl"


def test_plan_cli_prints_pdf_outputs(capsys):
    main(["plan", "--metadata-dir", str(FIXTURE_DIR)])

    output = capsys.readouterr().out

    assert "Planned PDF outputs:" in output
    assert "doc-root" in output
    assert "Root notebook.pdf" in output
