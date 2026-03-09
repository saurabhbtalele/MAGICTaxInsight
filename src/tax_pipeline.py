"""End-to-end tax form extraction pipeline.

Pipeline:
  1. Text Extraction  — pdfplumber for digital PDFs; Tesseract OCR for scanned pages
  2. Form Detection   — text-pattern matching against FORM_REGISTRY
  3. Field Extraction — dedicated parser per form_id, generic regex fallback
  4. JSON Output      — structured envelope matching DESIGN.md Section 7

Scanned PDF handling:
  pdfplumber extracts embedded text on each page.  If a page yields zero
  characters, it is considered a scanned (image-only) page and is re-processed
  by TesseractEngine, which renders the page at 300 DPI and runs Tesseract 5.
  The OCR text is then fed into the same detection and extraction layers.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict

import pdfplumber

from src.forms.detector import detect_forms
from src.forms.extractor import extract_forms
from src.models.document import ExtractedForm, ParsedDocument, ParsedPage
from src.utils import DocumentClassification, classify_pdf_pages
from src.utils.logger import log


def _build_document_digital(pdf_path: Path) -> tuple[ParsedDocument, str]:
    """Extract embedded text from a digital PDF using pdfplumber.

    Returns the ParsedDocument and the extraction tier label.
    """
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [
            ParsedPage(
                page_number=i + 1,
                raw_text=page.extract_text() or "",
            )
            for i, page in enumerate(pdf.pages)
        ]

    return (
        ParsedDocument(
            filename=pdf_path.name,
            total_pages=len(pages),
            pages=pages,
            metadata={"source_path": str(pdf_path)},
        ),
        "pdfplumber",
    )


def _build_document_ocr(pdf_path: Path) -> tuple[ParsedDocument, str]:
    """Extract text from a scanned PDF using Tesseract via TesseractEngine.

    Returns the ParsedDocument and the extraction tier label.
    """
    from src.ocr.tesseract_engine import TesseractEngine

    engine = TesseractEngine()
    ocr_pages = engine.extract_pages(pdf_path)

    pages = [
        ParsedPage(
            page_number=p.page_number,
            raw_text=p.text,
        )
        for p in ocr_pages
    ]

    # Store per-page OCR confidence in metadata for audit purposes
    ocr_confidences = {p.page_number: p.confidence for p in ocr_pages}

    return (
        ParsedDocument(
            filename=pdf_path.name,
            total_pages=len(pages),
            pages=pages,
            metadata={
                "source_path": str(pdf_path),
                "ocr_engine": "tesseract",
                "ocr_page_confidences": ocr_confidences,
            },
        ),
        "tesseract_ocr",
    )


def _build_document(pdf_path: Path) -> tuple[ParsedDocument, str]:
    """Build a ParsedDocument, routing to OCR automatically for scanned PDFs.

    Uses a dedicated page classifier to decide whether the document is entirely
    image-based (scanned) or contains selectable text.
    """
    classification: DocumentClassification = classify_pdf_pages(pdf_path)

    if classification.is_scanned_document:
        log.info(
            f"[pipeline] All {classification.total_pages} page(s) in "
            f"'{Path(pdf_path).name}' appear to be image-based. "
            "Routing to Tesseract OCR..."
        )
        document, tier = _build_document_ocr(pdf_path)
    else:
        document, tier = _build_document_digital(pdf_path)

    # Attach page-level classification metadata for downstream consumers
    page_type_map = {
        p.page_number: p.page_type.value for p in classification.pages
    }
    document.metadata.setdefault("source_path", str(pdf_path))
    document.metadata["page_classification"] = classification
    document.metadata["is_scanned_document"] = classification.is_scanned_document
    document.metadata["has_mixed_pages"] = classification.has_mixed_pages
    document.metadata["page_types"] = page_type_map

    if tier == "tesseract_ocr":
        total_chars = sum(len(p.raw_text) for p in document.pages)
        log.success(
            f"[pipeline] OCR complete — extracted {total_chars} characters "
            f"across {document.total_pages} page(s)."
        )

    return document, tier


def process_tax_package(pdf_path: str | Path) -> Dict[str, Any]:
    """Extract all IRS tax form fields from a PDF and return structured JSON.

    Automatically detects scanned PDFs and routes them through Tesseract OCR.

    Returns a dict matching the output schema defined in DESIGN.md Section 7:
      {
        "filename":      str,
        "total_pages":   int,
        "processed_at":  ISO-8601 str,
        "extraction_tier": "pdfplumber" | "tesseract_ocr",
        "forms":         [ ExtractedForm.to_dict(), ... ]
      }
    """
    pdf_path = Path(pdf_path)

    document, tier = _build_document(pdf_path)

    detected = detect_forms(document)
    extracted_dicts = extract_forms(document, detected)

    document.extracted_forms = [
        ExtractedForm(
            form_id=d["form_id"],
            display_name=d["display_name"],
            page_numbers=d["page_numbers"],
            fields=d["fields"],
            confidence=d["confidence"],
            tax_year=d.get("tax_year"),
            extraction_tier_used=d.get("extraction_tier_used", tier),
        )
        for d in extracted_dicts
    ]

    return {
        "filename": document.filename,
        "total_pages": document.total_pages,
        "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
        "extraction_tier": tier,
        "forms": [f.to_dict() for f in document.extracted_forms],
    }
