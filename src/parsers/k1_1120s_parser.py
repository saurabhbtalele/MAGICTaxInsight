"""Schedule K-1 (Form 1120-S) — Shareholder's Share of Income, Deductions, Credits, etc.

Strategy: pdfplumber text extraction + regex, no Azure DI model required.

K-1 (1120-S) layout (IRS standard + common tax-software variants):
  Part I   — Information About the Corporation (EIN, name, address, tax year)
  Part II  — Information About the Shareholder (TIN, name, allocation %)
  Part III — Shareholder's Share of Current Year Income/Deductions/Credits (Boxes 1–17)

MGIC-critical fields (used for self-employment / business income analysis):
  Box 1  Ordinary business income (loss)
  Box 2  Net rental real estate income (loss)
  Box 3  Other net rental income (loss)
  Box 4  Interest income
  Box 5a Ordinary dividends
  Box 5b Qualified dividends
  Box 6  Royalties
  Box 7  Net short-term capital gain (loss)
  Box 8a Net long-term capital gain (loss)
  Box 9  Net section 1231 gain (loss)
  Box 10 Other income (loss)
  Box 11 Section 179 deduction
  Box 16 Items affecting shareholder basis (distributions)
  Part II G — Shareholder's percentage of stock ownership

Negative amounts: IRS forms show losses in parentheses, e.g. (12,500.00).
Tax-software PDFs may also use a leading minus sign.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Shared helpers (mirrors k1_1065_parser conventions)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Collapse all whitespace to single spaces for uniform regex matching."""
    return re.sub(r"\s+", " ", text).strip()


def _first(pattern: str, text: str, group: int = 1) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        return m.group(group).strip()
    except IndexError:
        return m.group(0).strip()


def _to_float(value: str | None) -> float | None:
    """Convert a currency/numeric string to float; handles parenthetical negatives."""
    if value is None:
        return None
    v = value.strip()
    negative = v.startswith("(") and v.endswith(")")
    v = v.strip("()")
    v = v.replace(",", "").replace("$", "").strip()
    try:
        result = float(v)
        return -result if negative else result
    except ValueError:
        return None


def _to_pct(value: str | None) -> float | None:
    """Convert a percentage string such as '80%' or '0.80' to a 0–1 float."""
    if value is None:
        return None
    v = value.replace("%", "").replace(",", "").strip()
    try:
        f = float(v)
        return f / 100.0 if f > 1.0 else f
    except ValueError:
        return None


# Requires a decimal point + cents so bare box-label integers (e.g. 14, 15)
# are never confused for real currency values on partially blank forms.
_AMOUNT = r"(-?\(?\s*[\d,]+\.\d{1,2}\s*\)?)"


def _box_value(box_pattern: str, text: str) -> float | None:
    """Return the first numeric amount that follows a box label pattern."""
    m = re.search(
        rf"{box_pattern}"
        r"[^0-9($\-\n]{0,80}"
        + _AMOUNT,
        text, re.IGNORECASE | re.DOTALL,
    )
    return _to_float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Part I — Corporation information
# ---------------------------------------------------------------------------

def _extract_corporation_info(text: str) -> dict[str, Any]:
    """Extract entity-level fields from Part I."""
    ein_m = re.search(r"\b(\d{2}-\d{7})\b", text)
    ein = ein_m.group(1) if ein_m else None

    name = _first(
        r"(?:Corporation['']?s?\s+name|Name\s+of\s+(?:S[\s-]?)?corporation|S\s+corporation\s+name)"
        r"[^A-Z]{0,30}([A-Z][A-Za-z0-9\s&,.'()]{5,80})",
        text,
    )
    if name is None:
        # Fallback: common corporate suffixes
        name_m = re.search(
            r"\b([A-Z][A-Z0-9\s&,.']{5,70}"
            r"(?:INC|INC\.|CORP|CO\b|LTD|LLC|S\.?A\.|GROUP|SOLUTIONS|TECH|SERVICES|HOLDINGS))\b",
            text,
        )
        name = name_m.group(1).strip() if name_m else None

    return {
        "s_corp_ein": ein,
        "s_corp_name": name,
    }


# ---------------------------------------------------------------------------
# Part II — Shareholder information
# ---------------------------------------------------------------------------

def _extract_shareholder_info(text: str) -> dict[str, Any]:
    """Extract the shareholder-level fields from Part II."""
    tins = re.findall(r"\b(\d{2}-\d{7}|\d{3}-\d{2}-\d{4})\b", text)
    shareholder_tin = tins[1] if len(tins) >= 2 else (tins[0] if tins else None)

    shareholder_name = _first(
        r"(?:Shareholder['']?s?\s+name|Name\s+of\s+shareholder)[^A-Z]{0,30}"
        r"([A-Z][A-Za-z\s'.\-]{3,60})",
        text,
    )

    # Item G: percentage of stock ownership
    # Appears as "G   XX.XXXX%" or "Shareholder's percentage of stock ownership X%"
    ownership_pct = _to_pct(_first(
        r"(?:G\s+)?(?:Shareholder['']?s?\s+percentage\s+of\s+stock\s+ownership"
        r"|Percentage\s+of\s+(?:stock\s+)?ownership|Ownership\s+percentage)"
        r"[^\d%]{0,30}([\d.]+\s*%?)",
        text,
    ))
    if ownership_pct is None:
        # Fallback: Item G label with percentage
        ownership_pct = _to_pct(_first(
            r"\bG\b[^\d%]{0,40}([\d.]+\s*%)",
            text,
        ))

    return {
        "shareholder_tin": shareholder_tin,
        "shareholder_name": shareholder_name,
        "ownership_percentage": ownership_pct,
    }


# ---------------------------------------------------------------------------
# Part III — Income / Deduction boxes
# ---------------------------------------------------------------------------

def _extract_boxes(text: str) -> dict[str, Any]:
    """Extract Part III box values (Boxes 1–17)."""

    def box(pattern: str) -> float | None:
        return _box_value(pattern, text)

    # Box 1 — Ordinary business income (loss)  [MGIC-critical]
    box1 = (
        box(r"1\s+Ordinary\s+business\s+income\s*\(?loss\)?")
        or box(r"Ordinary\s+business\s+income\s*\(?loss\)?")
    )

    # Box 2 — Net rental real estate income (loss)
    box2 = box(r"2\s+Net\s+rental\s+real\s+estate\s+income\s*\(?loss\)?")

    # Box 3 — Other net rental income (loss)
    box3 = box(r"3\s+Other\s+net\s+rental\s+income\s*\(?loss\)?")

    # Box 4 — Interest income
    box4 = box(r"4\s+Interest\s+income")

    # Box 5a — Ordinary dividends
    box5a = (
        box(r"5[aA]\s+Ordinary\s+dividends")
        or box(r"5\s+Ordinary\s+dividends")
    )

    # Box 5b — Qualified dividends
    box5b = box(r"5[bB]\s+Qualified\s+dividends")

    # Box 6 — Royalties
    box6 = box(r"6\s+Royalties")

    # Box 7 — Net short-term capital gain (loss)
    box7 = (
        box(r"7\s+Net\s+short.?term\s+capital\s+gain\s*\(?loss\)?")
        or box(r"7\s+Short.?term\s+capital\s+gain\s*\(?loss\)?")
    )

    # Box 8a — Net long-term capital gain (loss)
    box8a = (
        box(r"8[aA]\s+Net\s+long.?term\s+capital\s+gain\s*\(?loss\)?")
        or box(r"8\s+Net\s+long.?term\s+capital\s+gain\s*\(?loss\)?")
    )

    # Box 8b — Collectibles (28%) gain (loss)
    box8b = box(r"8[bB]\s+Collectibles\s*\(?28%\)?\s*gain\s*\(?loss\)?")

    # Box 8c — Unrecaptured section 1250 gain
    box8c = box(r"8[cC]\s+Unrecaptured\s+section\s+1250")

    # Box 9 — Net section 1231 gain (loss)
    box9 = box(r"9\s+Net\s+section\s+1231\s+gain\s*\(?loss\)?")

    # Box 10 — Other income (loss)
    box10 = box(r"10\s+Other\s+income\s*\(?loss\)?")

    # Box 11 — Section 179 deduction
    box11 = box(r"11\s+Section\s+179\s+deduction")

    # Box 12 — Other deductions
    box12 = box(r"12\s+Other\s+deductions")

    # Box 13 — Credits
    box13 = box(r"13\s+Credits")

    # Box 16 — Items affecting shareholder basis (distributions)
    # IRS form lists multiple codes under Box 16 (D = cash distributions, etc.)
    # Capture the first amount under Box 16 and separately try code D.
    box16_any = box(r"16\s+Items\s+affecting\s+shareholder\s+basis")
    box16_distributions = (
        box(r"16\s*D\s+(?:Cash\s+(?:and\s+property\s+)?distributions?|Distributions?)")
        or box(r"Distributions?\s+(?:from\s+)?(?:the\s+)?(?:S\s+corp|corporation)")
        or box16_any
    )

    # Box 17 — Other information
    box17 = box(r"17\s+Other\s+information")

    return {
        "ordinary_business_income_loss_box_1": box1,
        "net_rental_real_estate_income_loss_box_2": box2,
        "other_net_rental_income_loss_box_3": box3,
        "interest_income_box_4": box4,
        "ordinary_dividends_box_5a": box5a,
        "qualified_dividends_box_5b": box5b,
        "royalties_box_6": box6,
        "net_short_term_capital_gain_loss_box_7": box7,
        "net_long_term_capital_gain_loss_box_8a": box8a,
        "collectibles_gain_loss_box_8b": box8b,
        "unrecaptured_sec1250_gain_box_8c": box8c,
        "net_section_1231_gain_loss_box_9": box9,
        "other_income_loss_box_10": box10,
        "section_179_deduction_box_11": box11,
        "other_deductions_box_12": box12,
        "credits_box_13": box13,
        "distributions_box_16": box16_distributions,
        "other_information_box_17": box17,
    }


# ---------------------------------------------------------------------------
# Tax year extraction
# ---------------------------------------------------------------------------

def _extract_tax_year(text: str) -> str | None:
    """Extract the tax year from the K-1 header."""
    m = re.search(
        r"(?:calendar\s+year|tax\s+year\s+(?:beginning|ending)?)[^0-9]{0,20}(20\d{2})",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m2 = re.search(
        r"Schedule\s+K-?1\s*\([^)]*1120-?S[^)]*\)[^0-9]{0,30}(20\d{2})",
        text, re.IGNORECASE,
    )
    return m2.group(1) if m2 else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_k1_1120s_from_text(text: str) -> dict[str, Any]:
    """Extract Schedule K-1 (Form 1120-S) fields from pre-extracted text.

    Accepts text obtained via pdfplumber or Tesseract OCR.
    """
    normalized = _normalize(text)
    result: dict[str, Any] = {}
    result.update(_extract_corporation_info(normalized))
    result.update(_extract_shareholder_info(normalized))
    result.update(_extract_boxes(normalized))
    result["tax_year"] = _extract_tax_year(normalized)
    return result


def extract_k1_1120s_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract Schedule K-1 (Form 1120-S) fields from a digital PDF.

    Opens the PDF with pdfplumber, joins all page text, then delegates
    to extract_k1_1120s_from_text for regex-based parsing.
    """
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("pdfplumber required. Run: pip install pdfplumber") from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(page.extract_text() or "" for page in pdf.pages)

    return extract_k1_1120s_from_text(raw)
