from __future__ import annotations

from pathlib import Path

import pytest

try:
    import fitz  # type: ignore[import]
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

try:
    import pdfplumber  # type: ignore[import]  # noqa:F401
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore[assignment]

from src.utils import PageType, classify_pdf_pages


pytestmark = pytest.mark.skipif(
    fitz is None or pdfplumber is None,
    reason="PyMuPDF (fitz) and pdfplumber are required for page classification tests.",
)


def _make_text_pdf(path: Path, text: str) -> None:
    """Create a single-page PDF with visible text using PyMuPDF."""
    assert fitz is not None
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), text)  # 1 inch from top-left
        doc.save(str(path))
    finally:
        doc.close()


def _make_blank_pdf(path: Path) -> None:
    """Create a single-page PDF with no text content."""
    assert fitz is not None
    doc = fitz.open()
    try:
        doc.new_page()
        doc.save(str(path))
    finally:
        doc.close()


def test_single_text_page_classified_as_selectable(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text_only.pdf"
    _make_text_pdf(pdf_path, "Hello IRS, this is a test W-2 form with wages 12345.")

    result = classify_pdf_pages(pdf_path)

    assert result.total_pages == 1
    assert result.all_selectable is True
    assert result.all_image is False
    assert result.has_mixed_pages is False

    page = result.pages[0]
    assert page.page_number == 1
    assert page.page_type is PageType.SELECTABLE_TEXT
    assert page.char_count > 0
    assert 0.0 <= page.image_area_ratio <= 1.0


def test_single_blank_page_classified_as_image(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf_path)

    result = classify_pdf_pages(pdf_path)

    assert result.total_pages == 1
    assert result.all_image is True
    assert result.all_selectable is False
    assert result.has_mixed_pages is False

    page = result.pages[0]
    assert page.page_number == 1
    assert page.page_type is PageType.IMAGE
    assert page.char_count == 0
    assert 0.0 <= page.image_area_ratio <= 1.0


def test_mixed_document_sets_has_mixed_pages(tmp_path: Path) -> None:
    # Two-page PDF: first page with text, second page blank
    assert fitz is not None
    pdf_path = tmp_path / "mixed.pdf"

    doc = fitz.open()
    try:
        page1 = doc.new_page()
        page1.insert_text((72, 72), "Page 1 has some selectable text.")

        doc.new_page()  # second page left blank

        doc.save(str(pdf_path))
    finally:
        doc.close()

    result = classify_pdf_pages(pdf_path)

    assert result.total_pages == 2
    assert result.has_mixed_pages is True
    assert result.all_selectable is False
    assert result.all_image is False

    page_types = {p.page_number: p.page_type for p in result.pages}
    assert page_types[1] is PageType.SELECTABLE_TEXT
    assert page_types[2] is PageType.IMAGE

