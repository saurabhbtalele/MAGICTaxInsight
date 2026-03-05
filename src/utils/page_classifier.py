from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List

import pdfplumber


class PageType(Enum):
    SELECTABLE_TEXT = "selectable_text"
    IMAGE = "image"


@dataclass
class PageClassification:
    page_number: int  # 1-based
    page_type: PageType
    confidence: float  # 0.0 – 1.0
    char_count: int  # characters extracted by pdfplumber
    image_area_ratio: float  # fraction of page area estimated as raster image


@dataclass
class DocumentClassification:
    source_path: str
    total_pages: int
    pages: List[PageClassification]
    has_mixed_pages: bool
    all_selectable: bool
    all_image: bool

    @property
    def is_scanned_document(self) -> bool:
        """Return True when every page appears image-based (no selectable text).

        This is the strict definition we use for \"scanned\" at the document
        level: if any page has embedded text, the document is not treated as
        scanned overall.
        """
        return self.all_image


def _estimate_image_area_ratio(page) -> float:
    """Estimate ratio of page area occupied by images using text blocks as proxy.

    We treat the union of text blocks as "text area" and assume the remaining
    area is dominated by raster content. This is a heuristic but works well
    enough to distinguish image-only pages from text-heavy layouts.
    """
    try:
        rect = page.rect
        page_area = float(rect.width * rect.height)
    except Exception:
        return 0.0

    if page_area <= 0:
        return 0.0

    text_blocks = page.get_text("blocks") or []
    text_area = 0.0

    for block in text_blocks:
        if len(block) < 5:
            continue
        x0, y0, x1, y1, text = block[:5]
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            width = max(0.0, float(x1) - float(x0))
            height = max(0.0, float(y1) - float(y0))
        except Exception:
            continue
        text_area += width * height

    if text_area <= 0:
        return 1.0

    if text_area >= page_area:
        return 0.0

    image_ratio = 1.0 - (text_area / page_area)
    return max(0.0, min(1.0, image_ratio))


def classify_pdf_pages(
    pdf_path: str | Path,
    text_char_threshold: int = 50,
    image_area_threshold: float = 0.8,
) -> DocumentClassification:
    """Classify each PDF page as selectable text or image-based.

    The primary signal is text density from pdfplumber. For pages with very
    little embedded text, we inspect layout via PyMuPDF to estimate how much
    of the page is covered by raster images.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for page classification. "
            "Run: pip install pymupdf"
        ) from exc

    pdf_path = Path(pdf_path)

    # First pass: character counts per page using pdfplumber
    char_counts: List[int] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            char_counts.append(len(text))

    # Second pass: structural inspection with PyMuPDF
    doc = fitz.open(str(pdf_path))
    pages: List[PageClassification] = []

    try:
        for index in range(len(doc)):
            page = doc[index]
            char_count = char_counts[index] if index < len(char_counts) else 0
            image_ratio = _estimate_image_area_ratio(page)

            if char_count >= text_char_threshold:
                page_type = PageType.SELECTABLE_TEXT
                confidence = 1.0
            else:
                # Low embedded text: rely more heavily on image ratio heuristic
                page_type = PageType.IMAGE
                confidence = 0.9 if image_ratio >= image_area_threshold else 0.6

            pages.append(
                PageClassification(
                    page_number=index + 1,
                    page_type=page_type,
                    confidence=confidence,
                    char_count=char_count,
                    image_area_ratio=image_ratio,
                )
            )
    finally:
        doc.close()

    total_pages = len(pages)
    page_types = {p.page_type for p in pages}

    all_selectable = bool(pages) and page_types == {PageType.SELECTABLE_TEXT}
    all_image = bool(pages) and page_types == {PageType.IMAGE}
    has_mixed_pages = (
        PageType.SELECTABLE_TEXT in page_types and PageType.IMAGE in page_types
    )

    return DocumentClassification(
        source_path=str(pdf_path),
        total_pages=total_pages,
        pages=pages,
        has_mixed_pages=has_mixed_pages,
        all_selectable=all_selectable,
        all_image=all_image,
    )

