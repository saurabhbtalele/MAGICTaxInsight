"""Form 1040 digital PDF extractor.

Approach: pdfplumber + whitespace normalisation + box-number-prefixed regex.

Key lines extracted (MGIC-relevant):
  Line 1a  Wages, salaries, tips
  Line 11  Adjusted gross income
  Line 15  Taxable income
  Line 24  Total tax
  Line 25  Federal income tax withheld (W-2 + 1099)
  Line 34  Refund amount
  Line 37  Amount you owe
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


# Regex to capture the FIRST dollar-amount (with optional commas) following
# a line-number label.  The (?!.*\d{4}) guard avoids matching SSNs or years.
_LINE = r"([\d,]+\.\d{2})"


def _extract_1040_fields(text: str) -> dict[str, Any]:
    """Core Form 1040 field extraction from normalised text."""
    def line(label_pattern: str) -> float | None:
        return _to_float(_first(label_pattern + r"[^0-9$]{0,60}" + _LINE, text))

    wages = line(r"1[aA]\s+Wages,\s*salaries") or line(r"1\s+Wages,\s*salaries")
    agi = line(r"11\s+Adjusted\s+gross\s+income") or line(r"Adjusted\s+gross\s+income")
    taxable_income = line(r"15\s+Taxable\s+income")
    total_tax = line(r"24\s+Total\s+tax")
    fed_withheld = (
        line(r"25[aA]\s+Federal\s+income\s+tax\s+withheld")
        or line(r"25\s+Federal\s+income\s+tax\s+withheld")
    )
    refund = line(r"34\s+Amount\s+of\s+line") or line(r"34\s+Refund")
    amount_owed = line(r"37\s+Amount\s+you\s+owe") or line(r"37\s+Amount\s+owe")

    taxpayer_name = _first(
        r"Your\s+first\s+name[^A-Z]{0,20}([A-Z][A-Za-z\s'.\-]{3,50})", text
    )
    taxpayer_ssn_m = re.search(
        r"Your\s+social\s+security\s+number[^0-9]{0,10}(\d{3}-\d{2}-\d{4})", text,
        re.IGNORECASE,
    )
    taxpayer_ssn = taxpayer_ssn_m.group(1) if taxpayer_ssn_m else None

    return {
        "wages_salaries_tips_line_1": wages,
        "adjusted_gross_income_line_11": agi,
        "taxable_income_line_15": taxable_income,
        "total_tax_line_24": total_tax,
        "federal_tax_withheld_line_25": fed_withheld,
        "amount_refunded_line_34": refund,
        "amount_owed_line_37": amount_owed,
        "taxpayer_name": taxpayer_name,
        "taxpayer_ssn": taxpayer_ssn,
    }


def extract_1040_from_text(text: str) -> dict[str, Any]:
    """Extract Form 1040 fields from pre-extracted (pdfplumber or OCR) text."""
    return _extract_1040_fields(_normalize(text))


def extract_1040_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract Form 1040 key lines from a digital PDF."""
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("pdfplumber required. Run: pip install pdfplumber") from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(p.extract_text() or "" for p in pdf.pages)

    return extract_1040_from_text(raw)
