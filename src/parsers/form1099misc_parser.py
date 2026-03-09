"""1099-MISC digital PDF extractor.

Approach (mirrors existing parser pattern):
  PDF → pdfplumber text → whitespace normalisation → regex → dict

Standard 1099-MISC layout:
  Boxes 1–18 covering rents, royalties, other income, fishing boat
  proceeds, medical/healthcare payments, substitute payments,
  crop insurance, attorney proceeds, and more.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Collapse whitespace to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def _first(pattern: str, text: str, group: int = 1) -> str | None:
    """Return first regex match group or ``None``."""
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        return m.group(group).strip()
    except IndexError:
        return m.group(0).strip()


def _to_float(v: str | None) -> float | None:
    """Parse a dollar amount string into a float."""
    if v is None:
        return None
    try:
        return float(v.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def _validate_tin(v: str | None) -> str | None:
    """Validate an EIN (XX-XXXXXXX) or SSN (XXX-XX-XXXX) pattern."""
    if v and re.match(
        r"[\dX*]{2}-[\dX*]{7}$|[\dX*]{3}-[\dX*]{2}-[\dX*]{4}$", v
    ):
        return v
    return None


# ---------------------------------------------------------------------------
# Box extraction helpers
# ---------------------------------------------------------------------------


def _extract_box(
    box_num: int | str,
    label: str,
    text: str,
) -> float | None:
    """Extract a numbered box value like '1 Rents   1,234.56'."""
    pattern = rf"{box_num}\s+{label}\s*([\d,]+\.?\d{{0,2}})"
    return _to_float(_first(pattern, text))


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract_1099misc_fields(text: str) -> dict[str, Any]:
    """Core 1099-MISC field extraction from normalised text."""
    return {
        # Identity
        "payer_tin": _validate_tin(
            _first(r"PAYER['']?S\s+TIN[^0-9]{0,10}(\d{2}-\d{7})", text)
        ),
        "recipient_tin": _validate_tin(
            _first(
                r"RECIPIENT['']?S\s+TIN[^0-9]{0,10}"
                r"([\dX*]{3}-[\dX*]{2}-[\dX*]{4}|\d{2}-\d{7})",
                text,
            )
        ),
        "payer_name": _first(
            r"^(.+?)(?=\s+PAYER['']?S\s+TIN|\s+\d{2}-\d{7})", text
        ),
        "recipient_name": _first(
            r"RECIPIENT['']?S\s+name[^A-Z]{0,20}([A-Z][A-Za-z\s'.\-]{3,50})",
            text,
        ),
        # Income boxes
        "rents_box_1": _extract_box(1, "Rents", text),
        "royalties_box_2": _extract_box(2, "Royalties", text),
        "other_income_box_3": _extract_box(3, r"Other\s+income", text),
        "federal_income_tax_withheld_box_4": _extract_box(
            4, r"Federal\s+income\s+tax\s+withheld", text
        ),
        "fishing_boat_proceeds_box_5": _extract_box(
            5, r"Fishing\s+boat\s+proceeds", text
        ),
        "medical_payments_box_6": _extract_box(
            6, r"Medical\s+and\s+health\s+care\s+payments", text
        ),
        "nonemployee_compensation_box_7": _extract_box(
            7, r"Nonemployee\s+compensation", text
        ),
        "substitute_payments_box_8": _extract_box(
            8, r"Substitute\s+payments", text
        ),
        "crop_insurance_box_10": _extract_box(
            10, r"Crop\s+insurance\s+proceeds", text
        ),
        "excess_golden_parachute_box_13": _extract_box(
            13, r"Excess\s+golden\s+parachute", text
        ),
        "gross_proceeds_attorney_box_14": _extract_box(
            14, r"Gross\s+proceeds.*?attorney", text
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_1099misc_from_text(text: str) -> dict[str, Any]:
    """Extract 1099-MISC fields from pre-extracted (pdfplumber or OCR) text."""
    return _extract_1099misc_fields(_normalize(text))


def extract_1099misc_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract 1099-MISC fields from a digital PDF."""
    try:
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber required. Run: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(p.extract_text() or "" for p in pdf.pages)

    return extract_1099misc_from_text(raw)
