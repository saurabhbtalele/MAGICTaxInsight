"""1099-NEC digital PDF extractor.

Approach (mirrors w2_parser.py):
  PDF → pdfplumber text → whitespace normalisation → regex → dict

Standard 1099-NEC layout:
  PAYER'S name, street address ...
  PAYER'S TIN    RECIPIENT'S TIN
  RECIPIENT'S name ...
  1 Nonemployee compensation   <amount>
  4 Federal income tax withheld <amount>
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _first(pattern: str, text: str, group: int = 1) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        return m.group(group).strip()
    except IndexError:
        return m.group(0).strip()


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def _validate_tin(v: str | None) -> str | None:
    if v and re.match(r"[\dX*]{2}-[\dX*]{7}$|[\dX*]{3}-[\dX*]{2}-[\dX*]{4}$", v):
        return v
    return None


def _extract_1099nec_fields(text: str) -> dict[str, Any]:
    """Core 1099-NEC field extraction from normalised text."""
    box1 = _to_float(_first(
        r"1\s+Nonemployee\s+compensation\s*([\d,]+\.\d{2})", text
    ))
    if box1 is None:
        box1 = _to_float(_first(
            r"Nonemployee\s+compensation\s*([\d,]+\.\d{2})", text
        ))

    box4 = _to_float(_first(
        r"4\s+Federal\s+income\s+tax\s+withheld\s*([\d,]+\.\d{2})", text
    ))

    payer_tin = _validate_tin(_first(
        r"PAYER['']?S\s+TIN[^0-9]{0,10}(\d{2}-\d{7})", text
    ))
    if payer_tin is None:
        payer_tin = _validate_tin(_first(r"(\d{2}-\d{7})", text))

    recipient_tin = _validate_tin(_first(
        r"RECIPIENT['']?S\s+TIN[^0-9]{0,10}([\dX*]{3}-[\dX*]{2}-[\dX*]{4}|\d{2}-\d{7})", text
    ))

    payer_name_m = re.search(
        r"^(.+?)(?=\s+PAYER['']?S\s+TIN|\s+\d{2}-\d{7})", text, re.IGNORECASE
    )
    payer_name = payer_name_m.group(1).strip() if payer_name_m else None

    recipient_name = _first(
        r"RECIPIENT['']?S\s+name[^A-Z]{0,20}([A-Z][A-Za-z\s'.\-]{3,50})", text
    )

    return {
        "nonemployee_compensation_box_1": box1,
        "federal_income_tax_withheld_box_4": box4,
        "payer_tin": payer_tin,
        "recipient_tin": recipient_tin,
        "payer_name": payer_name,
        "recipient_name": recipient_name,
    }


def extract_1099nec_from_text(text: str) -> dict[str, Any]:
    """Extract 1099-NEC fields from pre-extracted (pdfplumber or OCR) text."""
    return _extract_1099nec_fields(_normalize(text))


def extract_1099nec_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract 1099-NEC fields from a digital PDF."""
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("pdfplumber required. Run: pip install pdfplumber") from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(p.extract_text() or "" for p in pdf.pages)

    return extract_1099nec_from_text(raw)
