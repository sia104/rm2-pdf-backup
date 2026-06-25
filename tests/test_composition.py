from pathlib import Path

import pytest

from rm2_backup.pdf_compose import PdfCompositionError, compose_svg_pages_to_pdf


def test_compose_svg_pages_rejects_empty_input(tmp_path: Path) -> None:
    with pytest.raises(PdfCompositionError):
        compose_svg_pages_to_pdf((), tmp_path / "out.pdf")
