from __future__ import annotations

from pathlib import Path

from .excel import parse_excel
from .pdf import parse_pdf
from .pptx import parse_pptx


def parse_file(path: Path) -> dict:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return parse_excel(path)
    if suffix == ".pptx":
        return parse_pptx(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".ppt":
        return {
            "file_name": path.name,
            "file_type": "ppt",
            "documents": [],
            "numbers": [],
            "texts": [],
            "pages": [],
            "warnings": ["Legacy .ppt is not supported. Save as .pptx before upload."],
        }
    raise ValueError(f"Unsupported file type: {suffix}")
