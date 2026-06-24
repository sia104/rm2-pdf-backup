"""PDF validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PdfValidationResult:
    """Validation result for one PDF."""

    path: Path
    ok: bool
    reason: str


def validate_pdf(path: Path) -> PdfValidationResult:
    """Perform lightweight validation before publication."""

    if not path.exists():
        return PdfValidationResult(path, False, "PDF does not exist")
    if not path.is_file():
        return PdfValidationResult(path, False, "PDF path is not a file")
    data = path.read_bytes()
    if len(data) == 0:
        return PdfValidationResult(path, False, "PDF is empty")
    if not data.startswith(b"%PDF-"):
        return PdfValidationResult(path, False, "PDF header missing")
    if b"%%EOF" not in data[-2048:]:
        return PdfValidationResult(path, False, "PDF EOF marker missing")
    return PdfValidationResult(path, True, "ok")
