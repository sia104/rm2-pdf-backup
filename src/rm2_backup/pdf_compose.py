"""Compose rendered SVG pages into multi-page PDFs."""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from pathlib import Path


class PdfCompositionError(RuntimeError):
    """Raised when SVG-to-PDF composition fails."""


def compose_svg_pages_to_pdf(svg_paths: Sequence[Path], output_pdf: Path) -> Path:
    """Convert SVG pages to a single multi-page PDF.

    This uses the optional runtime dependencies ``cairosvg`` and ``pypdf``. They
    are kept here so renderer code remains independent of the PDF composition
    implementation.
    """

    if not svg_paths:
        raise PdfCompositionError("No SVG pages supplied for PDF composition")

    try:
        import cairosvg
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:  # pragma: no cover - exercised by deployment envs
        raise PdfCompositionError(
            "SVG-to-PDF composition requires cairosvg and pypdf to be installed"
        ) from exc

    writer = PdfWriter()
    for svg_path in svg_paths:
        if not svg_path.is_file() or svg_path.stat().st_size == 0:
            raise PdfCompositionError(f"SVG page is missing or empty: {svg_path}")
        try:
            page_pdf = BytesIO()
            cairosvg.svg2pdf(url=str(svg_path), write_to=page_pdf)
            page_pdf.seek(0)
            reader = PdfReader(page_pdf)
            if len(reader.pages) == 0:
                raise PdfCompositionError(f"SVG produced no PDF pages: {svg_path}")
            for page in reader.pages:
                writer.add_page(page)
        except PdfCompositionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive external-library boundary
            raise PdfCompositionError(f"Could not compose SVG page {svg_path}: {exc}") from exc

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    tmp_pdf = output_pdf.with_name(f".{output_pdf.name}.tmp")
    with tmp_pdf.open("wb") as handle:
        writer.write(handle)
    tmp_pdf.replace(output_pdf)
    return output_pdf
