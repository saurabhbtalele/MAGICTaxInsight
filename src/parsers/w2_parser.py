"""W-2 digital PDF extractor.

Uses pdfplumber + whitespace normalisation + regex, as described in
w2_extraction_implementation.md.  No OCR or ML required for digital PDFs.

Architecture (from guide):
  PDF → pdfplumber text extraction → whitespace normalisation
      → regex field extraction → normalisation → validation → dict

ADP-style W-2 layout observed in Santosh-W2.pdf:
  ...EIN  SSN
  1 Wages,tips,othercomp. 2 Federal income taxwithheld  <box1>  <box2>
  3 Social security wages 4 Social security taxwithheld  <box3>  <box4>
  5 Medicare wages andtips 6 Medicare taxwithheld         <box5>  <box6>
  ...
  12a... <employee_name> 12b <address>

Gross Pay <amount> appears earlier in the earnings-summary section and
is a reliable cross-check for Box 1.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Collapse all whitespace (including newlines) to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def _first(pattern: str, text: str, group: int = 1) -> str | None:
    """Return the first match of `group` (default 1), or None."""
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        return m.group(group).strip()
    except IndexError:
        return m.group(0).strip()


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("$", "").strip()
    try:
        v = float(cleaned)
        return v if v >= 0 else None
    except ValueError:
        return None


def _validate_ssn(v: str | None) -> str | None:
    if v and re.match(r"(?:[Xx*\d]{3}-[Xx*\d]{2}-)\d{4}$", v):
        return v
    return None


def _validate_ein(v: str | None) -> str | None:
    if v and re.match(r"\d{2}-\d{7}$", v):
        return v
    return None


# ---------------------------------------------------------------------------
# Box extraction patterns
# ---------------------------------------------------------------------------

def _extract_boxes(text: str) -> dict[str, float | None]:
    """Extract all numeric box values using the ADP-style paired layout."""

    # --- Box 1 & 2 ---
    # In the box grid: "1 Wages,... 2 Federal income taxwithheld <val1> <val2>"
    # val1 = Box 1 wages, val2 = Box 2 federal tax withheld.
    m12 = re.search(
        r"1\s+Wages[^0-9]{0,80}2\s+Federal income tax\s*withheld"
        r"\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
        text, re.IGNORECASE | re.DOTALL,
    )
    box1 = _to_float(m12.group(1)) if m12 else None
    box2 = _to_float(m12.group(2)) if m12 else None

    # Fallback for Box 1: earnings-summary "Gross Pay <amount>"
    if box1 is None:
        box1 = _to_float(_first(r"Gross Pay\s*([\d,]+\.?\d{0,2})", text))

    # Fallback for Box 2: first standalone amount after "Federal income tax withheld"
    # skipping any preceding wages figure.
    if box2 is None:
        m2f = re.search(
            r"Federal income tax\s*withheld"
            r"\s+[\d,]+\.\d{2}"        # skip wages that appear first
            r"\s+([\d,]+\.\d{2})",
            text, re.IGNORECASE | re.DOTALL,
        )
        box2 = _to_float(m2f.group(1)) if m2f else None

    # --- Box 3 & 4 ---
    # "3 Social security wages 4 Social security taxwithheld <val3> <val4>"
    m34 = re.search(
        r"3\s+Social security wages\s*4\s+Social security\s*tax\s*withheld"
        r"\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
        text, re.IGNORECASE | re.DOTALL,
    )
    box3 = _to_float(m34.group(1)) if m34 else None
    box4 = _to_float(m34.group(2)) if m34 else None

    # Fallback for Box 3 & 4: paired numbers after the combined label section.
    if box3 is None:
        m3f = re.search(
            r"Social security wages.*?Social security\s*tax\s*withheld"
            r"\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
            text, re.IGNORECASE | re.DOTALL,
        )
        box3 = _to_float(m3f.group(1)) if m3f else None
        box4 = _to_float(m3f.group(2)) if m3f else None

    # --- Box 5 & 6 ---
    # "5 Medicare wages andtips 6 Medicare taxwithheld <val5> <val6>"
    m56 = re.search(
        r"5\s+Medicare wages\s*(?:and)?\s*tips\s*6\s+Medicare\s*tax\s*withheld"
        r"\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
        text, re.IGNORECASE | re.DOTALL,
    )
    box5 = _to_float(m56.group(1)) if m56 else None
    box6 = _to_float(m56.group(2)) if m56 else None

    if box5 is None:
        m5f = re.search(
            r"Medicare wages\s*(?:and)?\s*tips.*?Medicare\s*tax\s*withheld"
            r"\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
            text, re.IGNORECASE | re.DOTALL,
        )
        box5 = _to_float(m5f.group(1)) if m5f else None
        box6 = _to_float(m5f.group(2)) if m5f else None

    return {
        "wages_tips_other_compensation_box_1": box1,
        "federal_income_tax_withheld_box_2": box2,
        "social_security_wages_box_3": box3,
        "social_security_tax_withheld_box_4": box4,
        "medicare_wages_tips_box_5": box5,
        "medicare_tax_withheld_box_6": box6,
    }


def _extract_identifiers(text: str) -> dict[str, str | None]:
    """Extract SSN, EIN, employee name, employer name."""

    # SSN (may be masked: XXX-XX-NNNN or full NNN-NN-NNNN)
    ssn_m = re.search(r"\b(\d{3}-\d{2}-\d{4})\b", text)
    if ssn_m is None:
        ssn_m = re.search(r"([Xx*]{3}-[Xx*]{2}-\d{4})", text)
    ssn = _validate_ssn(ssn_m.group(1) if ssn_m else None)

    # EIN — first occurrence of NN-NNNNNNN
    ein = _validate_ein(_first(r"\b(\d{2}-\d{7})\b", text))

    # Employee name: appears in the form body between "12a..." and "12b"
    # Pattern: after 12a instructions block, before "12b" box label.
    emp_m = re.search(
        r"12[aA]\s*(?:See\s*instructions)?[^A-Z]{0,50}"
        r"([A-Z][A-Z '.\-]{5,50})"
        r"(?=\s*12[bB]|\s*\d{4}\s)",
        text,
    )
    employee_name = emp_m.group(1).strip() if emp_m else None

    # Employer name: appears immediately after "Employer's name, address, and ZIP code"
    # label (field c on the W-2).  Grab all-caps words up to the street number.
    emp_name_m = re.search(
        r"Employer['']?s?\s*name[^A-Z]{0,50}"
        r"([A-Z][A-Z\s&,.'()]{5,80}?)"
        r"(?=\s+\d{2,5}\s+[A-Z]|\s+\d{5}|\s*,\s*[A-Z]{2})",
        text,
    )
    if emp_name_m is None:
        # Fallback: look for all-caps multi-word company name ending with INC/LLC/etc.
        emp_name_m = re.search(
            r"\b([A-Z][A-Z\s&,.']{5,60}(?:INC|LLC|CORP|CO\b|LTD|GROUP|SOLUTIONS))\b",
            text,
        )
    employer_name = emp_name_m.group(1).strip() if emp_name_m else None

    return {
        "employee_ssn": ssn,
        "employer_ein": ein,
        "employee_name": employee_name,
        "employer_name": employer_name,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_w2_from_text(text: str) -> dict[str, Any]:
    """Extract W-2 fields from pre-extracted (normalised or raw) text.

    Used when text has already been obtained via pdfplumber or OCR.
    """
    normalized = _normalize(text)
    result: dict[str, Any] = {}
    result.update(_extract_boxes(normalized))
    result.update(_extract_identifiers(normalized))
    return result


def extract_w2_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract W-2 fields from a digital (non-scanned) PDF.

    Opens the PDF with pdfplumber, extracts embedded text, then delegates
    to extract_w2_from_text for the regex parsing step.
    """
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is required. Run: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(page.extract_text() or "" for page in pdf.pages)

    return extract_w2_from_text(raw)
