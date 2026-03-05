"""Tesseract OCR engine for scanned (image-only) PDF pages.

Uses PyMuPDF (fitz) to render each PDF page to a high-resolution image,
then Tesseract 5 via pytesseract to extract text.

This is Layer 0 of the extraction pipeline — it runs only when pdfplumber
finds no embedded text, producing raw text that feeds the same
form detection and field extraction layers used for digital PDFs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

DPI = 300  # Render resolution; 300 DPI is standard for OCR on IRS forms


@dataclass
class OcrPage:
    page_number: int
    text: str
    confidence: float   # Mean Tesseract word confidence (0–100)


class TesseractEngine:
    """Renders a PDF to images and extracts text with Tesseract."""

    def extract_pages(self, pdf_path: str | Path) -> List[OcrPage]:
        """Return one OcrPage per PDF page, with OCR text and confidence."""
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError(
                "PyMuPDF is required for scanned PDF support. "
                "Run: pip install pymupdf"
            ) from exc

        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "pytesseract and Pillow are required for scanned PDF support. "
                "Run: pip install pytesseract Pillow"
            ) from exc

        pdf_path = Path(pdf_path)
        pages: List[OcrPage] = []

        doc = fitz.open(str(pdf_path))
        try:
            for page_index in range(len(doc)):
                page = doc[page_index]

                # Render page to a pixel map at target DPI
                zoom = DPI / 72  # PyMuPDF default is 72 DPI
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

                # Convert to Pillow Image for pytesseract
                img = Image.frombytes("L", [pix.width, pix.height], pix.samples)

                # Run Tesseract — get detailed data for confidence scoring
                tsv_data = pytesseract.image_to_data(
                    img,
                    output_type=pytesseract.Output.DICT,
                    config="--psm 6",  # Assume a uniform block of text
                )
                raw_text = pytesseract.image_to_string(img, config="--psm 6")

                # Compute mean confidence from words with valid readings
                confidences = [
                    int(c)
                    for c in tsv_data["conf"]
                    if str(c).lstrip("-").isdigit() and int(c) >= 0
                ]
                mean_conf = (sum(confidences) / len(confidences)) if confidences else 0.0

                pages.append(
                    OcrPage(
                        page_number=page_index + 1,
                        text=raw_text,
                        confidence=round(mean_conf, 1),
                    )
                )
        finally:
            doc.close()

        return pages
