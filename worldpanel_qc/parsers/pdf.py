from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from .pptx import _extract_numbers


def parse_pdf(path: Path) -> dict:
    reader = PdfReader(str(path))
    pages, numbers, texts = [], [], []
    for page_number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        page_numbers = _extract_numbers(text, text[:240], f"Page {page_number}", path.name)
        try:
            image_count = len(page.images)
        except Exception:
            image_count = 0
        review_required = len(text.strip()) < 40 or image_count > 0
        coverage = 55 if review_required else 90
        pages.append(
            {
                "page": page_number,
                "text": text,
                "numbers": page_numbers,
                "coverage_percent": coverage,
                "numbers_found": len(page_numbers),
                "low_confidence_count": image_count + int(len(text.strip()) < 40),
                "review_required": review_required,
                "detail": f"{image_count} image region(s); {'low extracted text' if len(text.strip()) < 40 else 'text layer extracted'}.",
            }
        )
        texts.append({"text": text, "location": f"Page {page_number}"})
        numbers.extend(page_numbers)
    return {
        "file_name": path.name,
        "file_type": "pdf",
        "numbers": numbers,
        "texts": texts,
        "pages": pages,
        "warnings": [],
    }
