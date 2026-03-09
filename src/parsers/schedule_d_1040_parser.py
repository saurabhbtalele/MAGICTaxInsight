"""Schedule D (Capital Gains and Losses) PDF extractor.

Handles:
  Part I  — Short-Term Capital Gains and Losses (Lines 1a–7)
  Part II — Long-Term Capital Gains and Losses  (Lines 8a–15)
  Part III — Summary (Lines 16, 21, 22)
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
    # Use non-greedy but require at least 2 digits before dot to skip line references
    pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]{{2,}}\.\d{{2}})\)?"
    raw = _first(pattern, text)
    if not raw:
        pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]+)\)?"
        raw = _first(pattern, text)
    return _to_float(raw)


def _neg_amount(line_num: int | str, label: str, text: str) -> float | None:
    """Extract an amount that may be negative (in parentheses)."""
    pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]{{2,}}\.\d{{2}})\)?"
    raw = _first(pattern, text)
    if not raw:
        pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]+)\)?"
        raw = _first(pattern, text)
    
    result = _to_float(raw)
    if result is not None:
        full_match = re.search(
            rf"{line_num}\s+{label}.{0,150}?\s\(([\d,]+\.?\d{{0,2}})\)",
            text,
            re.IGNORECASE,
        )
        if full_match:
            result = -abs(result)
    return result


# ---------------------------------------------------------------------------
# Transaction row extraction
# ---------------------------------------------------------------------------


def _extract_transaction_rows(text: str, start_marker: str, end_marker: str) -> list[dict[str, Any]]:
    """Extract capital gain/loss transaction rows between markers.

    Typical row format:
      100 sh XYZ Corp   01/15/2023  06/20/2023  15,000  10,000  5,000
    """
    start_idx = text.lower().find(start_marker.lower())
    end_idx = text.lower().find(end_marker.lower())
    if start_idx == -1:
        return []
    block = text[start_idx:end_idx] if end_idx != -1 else text[start_idx:]

    rows: list[dict[str, Any]] = []
    # Match: description, optional dates, then 2-3 dollar amounts
    for m in re.finditer(
        r"([A-Za-z][\w\s.,'&\-]{2,40}?)\s+"
        r"(\d{1,2}/\d{1,2}/\d{2,4})?\s*"
        r"(\d{1,2}/\d{1,2}/\d{2,4})?\s+"
        r"([\d,]+\.?\d{0,2})\s+"
        r"([\d,]+\.?\d{0,2})\s*"
        r"\(?([\d,]+\.?\d{0,2})\)?",
        block,
    ):
        rows.append({
            "description": m.group(1).strip(),
            "date_acquired": m.group(2),
            "date_sold": m.group(3),
            "proceeds": _to_float(m.group(4)),
            "cost_basis": _to_float(m.group(5)),
            "gain_or_loss": _to_float(m.group(6)),
        })
    return rows


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract_schedule_d_fields(text: str) -> dict[str, Any]:
    """Core Schedule D field extraction from normalised text."""
    # Part I — Short-Term
    short_term = _extract_transaction_rows(text, "Part I", "Part II")
    line_7_total = _neg_amount(7, r"(?:Net\s+short-term|Total)", text)

    # Part II — Long-Term
    long_term = _extract_transaction_rows(text, "Part II", "Part III")
    line_15_total = _neg_amount(15, r"(?:Net\s+long-term|Total)", text)

    # Part III — Summary
    line_16 = _neg_amount(16, r"(?:Combine|line)", text)
    line_21 = _neg_amount(21, r"(?:Combine|Net)", text)
    line_22 = _first(
        r"22\s+.*?(Yes|No)", text
    )

    return {
        "short_term_transactions": short_term,
        "net_short_term_gain_loss_line_7": line_7_total,
        "long_term_transactions": long_term,
        "net_long_term_gain_loss_line_15": line_15_total,
        "combined_line_16": line_16,
        "combined_line_21": line_21,
        "qualified_dividends_worksheet_line_22": line_22,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_schedule_d_1040_from_text(text: str) -> dict[str, Any]:
    """Parse a full Schedule D (1040) text dump."""
    return _extract_schedule_d_fields(_normalize(text))


def extract_schedule_d_1040_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract Schedule D (1040) data directly from a digital PDF using pdfplumber.
    """
    import pdfplumber

    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_pages.append(page.extract_text() or "")
    
    raw = "\n".join(text_pages)
    return extract_schedule_d_1040_from_text(raw)
