"""Schedule E (Supplemental Income and Loss) PDF extractor.

Handles:
  Part I  — Income or Loss From Rental Real Estate and Royalties
             (up to 3 properties per page in columns A, B, C)
  Part II — Income or Loss From Partnerships and S Corporations
  Part III — Income or Loss From Estates and Trusts
  Part IV  — Income or Loss From REMICs
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


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
        cleaned = v.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
        return float(cleaned)
    except ValueError:
        return None


def _line_amount(line_num: int | str, label: str, text: str) -> float | None:
    pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]+\.\d{{2}})\)?"
    raw = _first(pattern, text)
    if not raw:
        pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]+)\)?"
        raw = _first(pattern, text)
    return _to_float(raw)


# ---------------------------------------------------------------------------
# Property extraction (Part I)
# ---------------------------------------------------------------------------


def _extract_property_block(text: str, prop_letter: str) -> dict[str, Any] | None:
    """Extract a single property column (A, B, or C) from Part I."""
    # Try to find the property address line
    addr_match = re.search(
        rf"(?:1[abc]|{prop_letter})\s+(?:Physical\s+address|street).*?([A-Z0-9][\w\s,.\-#]+)",
        text,
        re.IGNORECASE,
    )
    if not addr_match:
        # Try generic property address pattern
        addr_match = re.search(
            rf"{prop_letter}\s*[:\s]+([\d]+[\w\s,.\-#]+)",
            text,
            re.IGNORECASE,
        )

    address = addr_match.group(1).strip() if addr_match else None

    # Property type
    prop_type = _first(
        rf"(?:2|Type).*?{prop_letter}.*?(Single|Multi|Vacation|Commercial|Land|Other|Self-Rental)",
        text,
    )

    # Fair rental days / personal use days
    fair_rental = _to_float(_first(
        rf"(?:fair\s+rental|rental\s+days).*?{prop_letter}.*?(\d+)", text
    ))
    personal_use = _to_float(_first(
        rf"(?:personal\s+use|personal\s+days).*?{prop_letter}.*?(\d+)", text
    ))

    if not address and not prop_type and fair_rental is None:
        return None

    return {
        "address": address,
        "property_type": prop_type,
        "fair_rental_days": fair_rental,
        "personal_use_days": personal_use,
    }


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract_schedule_e_fields(text: str) -> dict[str, Any]:
    """Core Schedule E field extraction from normalised text."""
    # Part I — Rental Real Estate / Royalties
    properties: list[dict[str, Any]] = []
    for letter in ("A", "B", "C"):
        prop = _extract_property_block(text, letter)
        if prop:
            properties.append(prop)

    # Rents received (Line 3)
    rents_received = _line_amount(3, r"Rents\s+received", text)

    # Royalties received (Line 4)
    royalties_received = _line_amount(4, r"Royalties\s+received", text)

    # Expenses (Lines 5–19)
    expenses = {
        "advertising_line_5": _line_amount(5, r"Advertising", text),
        "auto_travel_line_6": _line_amount(6, r"Auto\s+and\s+travel", text),
        "cleaning_maintenance_line_7": _line_amount(7, r"Cleaning\s+and\s+maintenance", text),
        "commissions_line_8": _line_amount(8, r"Commissions", text),
        "insurance_line_9": _line_amount(9, r"Insurance", text),
        "legal_professional_line_10": _line_amount(10, r"Legal\s+and.*?professional", text),
        "management_fees_line_11": _line_amount(11, r"Management\s+fees", text),
        "mortgage_interest_line_12": _line_amount(12, r"Mortgage\s+interest", text),
        "other_interest_line_13": _line_amount(13, r"Other\s+interest", text),
        "repairs_line_14": _line_amount(14, r"Repairs", text),
        "supplies_line_15": _line_amount(15, r"Supplies", text),
        "taxes_line_16": _line_amount(16, r"Taxes", text),
        "utilities_line_17": _line_amount(17, r"Utilities", text),
        "depreciation_line_18": _line_amount(18, r"Depreciation", text),
        "other_line_19": _line_amount(19, r"Other", text),
    }

    # Total expenses (Line 20)
    total_expenses = _line_amount(20, r"Total\s+expenses", text)

    # Income or loss (Line 21)
    income_or_loss = _line_amount(21, r"(?:Income|loss)", text)

    # Total rental real estate income/loss (Line 26)
    total_line_26 = _line_amount(26, r"Total\s+rental\s+real\s+estate", text)

    # Part II — Partnerships / S Corps (summary)
    partnerships_total = _line_amount(32, r"Total\s+partnership", text)

    # Part III — Estates & Trusts (summary)
    estates_total = _line_amount(37, r"Total\s+estate", text)

    # Overall total (Line 41)
    total_line_41 = _line_amount(41, r"Total\s+(?:supplemental|income)", text)

    return {
        "properties": properties,
        "rents_received_line_3": rents_received,
        "royalties_received_line_4": royalties_received,
        "expenses": expenses,
        "total_expenses_line_20": total_expenses,
        "income_or_loss_line_21": income_or_loss,
        "total_rental_real_estate_line_26": total_line_26,
        "partnerships_total_line_32": partnerships_total,
        "estates_total_line_37": estates_total,
        "total_supplemental_income_line_41": total_line_41,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_schedule_e_1040_from_text(text: str) -> dict[str, Any]:
    """Parse a full Schedule E (1040) text dump."""
    return _extract_schedule_e_fields(_normalize(text))


def extract_schedule_e_1040_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract Schedule E (1040) data directly from a digital PDF using pdfplumber.
    """
    import pdfplumber

    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_pages.append(page.extract_text() or "")
    
    raw = "\n".join(text_pages)
    return extract_schedule_e_1040_from_text(raw)
