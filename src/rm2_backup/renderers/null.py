"""Placeholder renderer used for pipeline tests."""

from __future__ import annotations

from pathlib import Path

from rm2_backup.render_queue import RenderPlanItem
from rm2_backup.renderers.base import RenderResult

_MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 0 >>
stream

endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000202 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
251
%%EOF
"""


class PlaceholderRenderer:
    """Render a minimal single-page PDF for pipeline tests."""

    def render(self, item: RenderPlanItem, *, raw_xochitl: Path, staging_pdf: Path) -> RenderResult:
        """Write a minimal PDF to the requested staging path."""

        del raw_xochitl
        staging_pdf.parent.mkdir(parents=True, exist_ok=True)
        staging_pdf.write_bytes(_MINIMAL_PDF)
        return RenderResult(uuid=item.uuid, ok=True, output_path=staging_pdf)
