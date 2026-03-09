"""Schedule B (Interest and Ordinary Dividends) PDF extractor.

Handles:
  Part I  — Interest: list of payer-name / amount pairs + Line 4 total
  Part II — Ordinary Dividends: payer-name / amount pairs + Line 6 total
  Part III — Foreign Accounts / Trusts: yes/no + country
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


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# List extractors
# ---------------------------------------------------------------------------


def _extract_payer_rows(
    text: str,
    start_marker: str,
    end_marker: str,
) -> list[dict[str, Any]]:
    """Extract payer name + amount rows between two markers.

    IRS Schedule B lists each payer on its own line followed by an amount:
      ``Acme Bank                            1,234.56``
    """
    # Isolate the block
    start_idx = text.lower().find(start_marker.lower())
    end_idx = text.lower().find(end_marker.lower())
    if start_idx == -1:
        return []
    block = text[start_idx:end_idx] if end_idx != -1 else text[start_idx:]

    rows: list[dict[str, Any]] = []
    for m in re.finditer(
        r"([A-Z][A-Za-z\s&.,'\-]{2,60}?)\s+([\d,]+\.?\d{0,2})\b",
        block,
    ):
        payer = m.group(1).strip()
        amount = _to_float(m.group(2))
        if amount is not None and payer:
            rows.append({"payer": payer, "amount": amount})
    return rows


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract_schedule_b_fields(text: str) -> dict[str, Any]:
    """Core Schedule B field extraction from normalised text."""
    # Part I — Interest
    interest_rows = _extract_payer_rows(text, "Part I", "Part II")
    line_4_match = re.search(
        r"4\s+(?:Total|Add).*?\s([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )
    line_4_total = _to_float(line_4_match.group(1)) if line_4_match else None

    # Part II — Ordinary Dividends
    dividend_rows = _extract_payer_rows(text, "Part II", "Part III")
    line_6_match = re.search(
        r"6\s+(?:Total|Add).*?\s([\d,]+\.\d{2})",
        text,
        re.IGNORECASE,
    )
    line_6_total = _to_float(line_6_match.group(1)) if line_6_match else None

    # Part III — Foreign Accounts
    has_foreign = bool(
        re.search(r"(?:7a|Part\s+III).*?Yes", text, re.IGNORECASE)
    )
    # Target line 8 specifically to avoid over-matching "country" in 7a
    country_match = re.search(
        r"\b8\s+(?:Country\s*)?[:\s]*([A-Z][a-zA-Z\s]{2,30})",
        text,
        re.IGNORECASE,
    )
    foreign_country = None
    if country_match:
        val = country_match.group(1).strip()
        if val.lower() not in ("country", "is"):
            foreign_country = val
    
    return {
        "interest_payers": interest_rows,
        "interest_total_line_4": line_4_total,
        "dividend_payers": dividend_rows,
        "dividend_total_line_6": line_6_total,
        "foreign_accounts": has_foreign,
        "foreign_country": foreign_country,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_schedule_b_1040_from_text(text: str) -> dict[str, Any]:
    """Parse a full Schedule B (1040) text dump."""
    return _extract_schedule_b_fields(_normalize(text))


def extract_schedule_b_1040_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract Schedule B (1040) data directly from a digital PDF using pdfplumber.
    """
    try:
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber required. Run: pip install pdfplumber"
        ) from exc

    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_pages.append(page.extract_text() or "")
    
    raw = "\n".join(text_pages)
    return extract_schedule_b_1040_from_text(raw)
