"""Schedule K-1 (Form 1065) — Partner's Share of Income, Deductions, Credits, etc.

Strategy: pdfplumber text extraction + regex, no Azure DI model required.

K-1 (1065) layout (IRS standard + common tax-software variants):
  Part I   — Information About the Partnership (EIN, name, address)
  Part II  — Information About the Partner (TIN, name, share %, liabilities)
  Part III — Partner's Share of Current Year Income/Deductions/Credits (Boxes 1–23)

MGIC-critical fields (used for self-employment income calculation):
  Box 1  Ordinary business income (loss)
  Box 2  Net rental real estate income (loss)
  Box 3  Other net rental income (loss)
  Box 4  Guaranteed payments (services, capital, total)
  Box 5  Interest income
  Box 6a Ordinary dividends
  Box 9a Net long-term capital gain (loss)
  Box 10 Net section 1231 gain (loss)
  Box 12 Section 179 deduction
  Box 14 Self-employment earnings (loss)
  Box 19 Distributions
  Part II J — Partner's share profit/loss/capital %

Negative amounts: IRS forms show losses in parentheses, e.g. (12,500.00).
Tax-software PDFs may also use a leading minus sign.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Shared helpers
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
    """Convert a percentage string such as '50%' or '0.50' to a 0–1 float."""
    if value is None:
        return None
    v = value.replace("%", "").replace(",", "").strip()
    try:
        f = float(v)
        # Values > 1 are already in percentage form (e.g. 50.0 → 0.50)
        return f / 100.0 if f > 1.0 else f
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Regex helper — extract the first amount following a labelled box
# ---------------------------------------------------------------------------

# Requires a decimal point + cents so bare box-label integers (e.g. 14, 15)
# are never confused for real currency values on partially blank forms.
_AMOUNT = r"(-?\(?\s*[\d,]+\.\d{1,2}\s*\)?)"


def _box_value(box_pattern: str, text: str) -> float | None:
    """Return the first numeric amount that follows a box label pattern."""
    m = re.search(
        rf"{box_pattern}"               # box label (caller supplies the pattern)
        r"[^0-9($\-\n]{0,80}"          # skip label text — stop at first digit/sign
        + _AMOUNT,
        text, re.IGNORECASE | re.DOTALL,
    )
    return _to_float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Part I — Partnership information
# ---------------------------------------------------------------------------

def _extract_partnership_info(text: str) -> dict[str, Any]:
    """Extract the entity-level fields from Part I."""
    # EIN: NN-NNNNNNN
    ein_m = re.search(r"\b(\d{2}-\d{7})\b", text)
    ein = ein_m.group(1) if ein_m else None

    # Partnership name appears after "Partnership's name" or "Name of partnership"
    # or immediately before the EIN block in most software outputs.
    name = _first(
        r"(?:Partnership['']?s?\s+name|Name\s+of\s+partnership)[^A-Z]{0,30}"
        r"([A-Z][A-Za-z0-9\s&,.'()]{5,80})",
        text,
    )
    if name is None:
        # Fallback: all-caps entity name ending with LLC/LP/LLP/PLLC/INC etc.
        name_m = re.search(
            r"\b([A-Z][A-Z0-9\s&,.']{5,70}"
            r"(?:LLC|LP|LLP|PLLC|INC|INC\.|CORP|CO\b|LTD|PARTNERS|FUND))\b",
            text,
        )
        name = name_m.group(1).strip() if name_m else None

    return {
        "partnership_ein": ein,
        "partnership_name": name,
    }


# ---------------------------------------------------------------------------
# Part II — Partner information
# ---------------------------------------------------------------------------

def _extract_partner_info(text: str) -> dict[str, Any]:
    """Extract the partner-level fields from Part II."""
    # Partner TIN (SSN or EIN) — second TIN in the document (first is the partnership's)
    tins = re.findall(r"\b(\d{2}-\d{7}|\d{3}-\d{2}-\d{4})\b", text)
    partner_tin = tins[1] if len(tins) >= 2 else (tins[0] if tins else None)

    # Partner name
    partner_name = _first(
        r"(?:Partner['']?s?\s+name|Name\s+of\s+partner)[^A-Z]{0,30}"
        r"([A-Z][A-Za-z\s'.\-]{3,60})",
        text,
    )

    # Ownership/profit percentage — "J Profit X%" or "Profit ... X%"
    # IRS K-1 Part II, Item J lists Profit / Loss / Capital as separate rows.
    profit_pct = _to_pct(_first(
        r"(?:J\s+)?(?:Profit|Ownership\s+percentage)[^\d%]{0,30}([\d.]+\s*%?)",
        text,
    ))
    # If profit % not found try "ending" % near profit/loss/capital
    if profit_pct is None:
        profit_pct = _to_pct(_first(
            r"Profit.*?Ending\s+([\d.]+\s*%)",
            text,
        ))

    return {
        "partner_tin": partner_tin,
        "partner_name": partner_name,
        "ownership_percentage": profit_pct,
    }


# ---------------------------------------------------------------------------
# Part III — Income / Deduction boxes
# ---------------------------------------------------------------------------

def _extract_boxes(text: str) -> dict[str, Any]:
    """Extract Part III box values (Boxes 1–23)."""

    def box(pattern: str) -> float | None:
        return _box_value(pattern, text)

    # Box 1 — Ordinary business income (loss)
    box1 = (
        box(r"1\s+Ordinary\s+business\s+income\s*\(?loss\)?")
        or box(r"Ordinary\s+business\s+income\s*\(?loss\)?")
    )

    # Box 2 — Net rental real estate income (loss)
    box2 = box(r"2\s+Net\s+rental\s+real\s+estate\s+income\s*\(?loss\)?")

    # Box 3 — Other net rental income (loss)
    box3 = box(r"3\s+Other\s+net\s+rental\s+income\s*\(?loss\)?")

    # Box 4 — Guaranteed payments
    # IRS 2022+ splits this into 4a (services), 4b (capital), 4c (total).
    # Older forms and many software packages show a single "Guaranteed payments" box.
    gp_services = (
        box(r"4[aA]\s+Guaranteed\s+payments\s+for\s+services")
        or box(r"4[aA]\s+(?:GP\s+)?[Ss]ervices")
    )
    gp_capital = (
        box(r"4[bB]\s+Guaranteed\s+payments\s+for\s+capital")
        or box(r"4[bB]\s+(?:GP\s+)?[Cc]apital")
    )
    gp_total = (
        box(r"4[cC]\s+Total\s+guaranteed\s+payments")
        or box(r"4[cC]\s+Total\s+GP")
        or box(r"4\s+Guaranteed\s+payments")
        or box(r"Guaranteed\s+payments\s+(?:to\s+partner|for\s+capital\s+and\s+services)")
    )

    # Box 5 — Interest income
    box5 = box(r"5\s+Interest\s+income")

    # Box 6a — Ordinary dividends
    box6a = (
        box(r"6[aA]\s+Ordinary\s+dividends")
        or box(r"6\s+Ordinary\s+dividends")
    )

    # Box 6b — Qualified dividends
    box6b = box(r"6[bB]\s+Qualified\s+dividends")

    # Box 7 — Royalties
    box7 = box(r"7\s+Royalties")

    # Box 8 — Net short-term capital gain (loss)
    box8 = (
        box(r"8\s+Net\s+short.?term\s+capital\s+gain\s*\(?loss\)?")
        or box(r"8\s+Short.?term\s+capital\s+gain\s*\(?loss\)?")
    )

    # Box 9a — Net long-term capital gain (loss)
    box9a = (
        box(r"9[aA]\s+Net\s+long.?term\s+capital\s+gain\s*\(?loss\)?")
        or box(r"9\s+Net\s+long.?term\s+capital\s+gain\s*\(?loss\)?")
    )

    # Box 9b — Collectibles (28%) gain (loss)
    box9b = box(r"9[bB]\s+Collectibles\s*\(?28%\)?\s*gain\s*\(?loss\)?")

    # Box 9c — Unrecaptured section 1250 gain
    box9c = box(r"9[cC]\s+Unrecaptured\s+section\s+1250")

    # Box 10 — Net section 1231 gain (loss)
    box10 = box(r"10\s+Net\s+section\s+1231\s+gain\s*\(?loss\)?")

    # Box 11 — Other income (loss)
    box11 = box(r"11\s+Other\s+income\s*\(?loss\)?")

    # Box 12 — Section 179 deduction
    box12 = box(r"12\s+Section\s+179\s+deduction")

    # Box 13 — Other deductions (first code/amount pair)
    box13 = box(r"13\s+Other\s+deductions")

    # Box 14 — Self-employment earnings (loss)  [MGIC-critical]
    box14 = (
        box(r"14\s+Self.?employment\s+earnings\s*\(?loss\)?")
        or box(r"14\s+Self.?employment")
    )

    # Box 15 — Credits
    box15 = box(r"15\s+Credits")

    # Box 19 — Distributions
    box19 = (
        box(r"19\s+Distributions")
        or box(r"19[aA]\s+Cash\s+and\s+marketable\s+securities")
    )

    # Box 20 — Other information (first code found)
    box20 = box(r"20\s+Other\s+information")

    return {
        "ordinary_business_income_loss_box_1": box1,
        "net_rental_real_estate_income_loss_box_2": box2,
        "other_net_rental_income_loss_box_3": box3,
        "guaranteed_payments_services_box_4a": gp_services,
        "guaranteed_payments_capital_box_4b": gp_capital,
        "guaranteed_payments_total_box_4c": gp_total,
        "interest_income_box_5": box5,
        "ordinary_dividends_box_6a": box6a,
        "qualified_dividends_box_6b": box6b,
        "royalties_box_7": box7,
        "net_short_term_capital_gain_loss_box_8": box8,
        "net_long_term_capital_gain_loss_box_9a": box9a,
        "collectibles_gain_loss_box_9b": box9b,
        "unrecaptured_sec1250_gain_box_9c": box9c,
        "net_section_1231_gain_loss_box_10": box10,
        "other_income_loss_box_11": box11,
        "section_179_deduction_box_12": box12,
        "other_deductions_box_13": box13,
        "self_employment_earnings_loss_box_14": box14,
        "credits_box_15": box15,
        "distributions_box_19": box19,
        "other_information_box_20": box20,
    }


# ---------------------------------------------------------------------------
# Tax year extraction
# ---------------------------------------------------------------------------

def _extract_tax_year(text: str) -> str | None:
    """Extract the tax year from the K-1 header (e.g. 'For calendar year 2024')."""
    m = re.search(
        r"(?:calendar\s+year|tax\s+year\s+(?:beginning|ending)?)[^0-9]{0,20}(20\d{2})",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # Fallback: standalone 4-digit year near the form title
    m2 = re.search(
        r"Schedule\s+K-?1\s*\([^)]*1065[^)]*\)[^0-9]{0,30}(20\d{2})",
        text, re.IGNORECASE,
    )
    return m2.group(1) if m2 else None


# ---------------------------------------------------------------------------
# Coordinate-based extraction
# ---------------------------------------------------------------------------
# Some Form 1065 / Schedule K PDFs render values in a right-margin column
# (x0 > ~500 pt) rather than inline with their label text.  When pdfplumber
# reads such pages top-to-bottom it clusters the right-column values together,
# breaking plain regex.  This fallback groups words by row and matches each
# value to its label via Y-coordinate proximity.

_VALUE_X_THRESHOLD = 500  # points — values in the right column sit beyond this
_ROW_TOLERANCE = 4        # points — rows within this range share the same "slot"


def _parse_raw_amount(text: str) -> float | None:
    """
    Parse a raw word token that may be:
      • A plain integer:          "7,350" or "88138"
      • A decimal amount:         "62,000.00"
      • A parenthetical loss:     "(18,500)"
      • A statement+amount token: "Ste#3___4,034"  → extract trailing number
    """
    t = text.strip()
    negative = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    # Strip any leading non-numeric prefix (e.g. "Ste#3___")
    t = re.sub(r"^[^0-9\-]*", "", t)
    t = t.replace(",", "").replace("$", "").strip()
    if not t:
        return None
    try:
        val = float(t)
        return -val if negative else val
    except ValueError:
        return None


def _build_coord_row_map(pdf_path: str | Path) -> tuple[list[dict], dict[int, float]]:
    """
    Return (all_words, row_value_map) where:
      • all_words       — raw pdfplumber word dicts (text, x0, top, x1, bottom)
      • row_value_map   — {row_key: float}  right-column numeric values keyed by
                          rounded top coordinate
    """
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("pdfplumber required. Run: pip install pdfplumber") from exc

    all_words: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            all_words.extend(page.extract_words())

    row_value_map: dict[int, float] = {}
    for w in all_words:
        if w["x0"] >= _VALUE_X_THRESHOLD:
            val = _parse_raw_amount(w["text"])
            if val is not None:
                row_key = round(w["top"] / _ROW_TOLERANCE) * _ROW_TOLERANCE
                # Keep the first (topmost) value if multiple appear on the same key
                row_value_map.setdefault(row_key, val)

    return all_words, row_value_map


def _coord_lookup(
    label_pattern: str,
    all_words: list[dict],
    row_value_map: dict[int, float],
) -> float | None:
    """
    Find the row whose left-column text matches label_pattern (regex), then
    return the right-column value on the same row (within ±_ROW_TOLERANCE).
    """
    # Build row → concatenated label text (left column only)
    row_labels: dict[int, list[tuple[float, str]]] = {}
    for w in all_words:
        if w["x0"] < _VALUE_X_THRESHOLD:
            row_key = round(w["top"] / _ROW_TOLERANCE) * _ROW_TOLERANCE
            row_labels.setdefault(row_key, []).append((w["x0"], w["text"]))

    for row_key, word_list in sorted(row_labels.items()):
        label_text = " ".join(t for _, t in sorted(word_list))
        if re.search(label_pattern, label_text, re.IGNORECASE):
            # Only search ±1 slot — wider offsets bleed into neighboring rows
            for offset in (0, _ROW_TOLERANCE, -_ROW_TOLERANCE):
                v = row_value_map.get(row_key + offset)
                if v is not None:
                    return v
    return None


def _extract_boxes_by_coords(
    all_words: list[dict],
    row_value_map: dict[int, float],
) -> dict[str, Any]:
    """Extract Part III box values using coordinate-based row matching.

    Note: box numbers (1, 2, 4a …) often render on a slightly different top
    coordinate than their label text.  Patterns here match on the label text
    alone (no leading box number) so the regex is robust to that split.
    """

    def cb(pattern: str) -> float | None:
        return _coord_lookup(pattern, all_words, row_value_map)

    return {
        "ordinary_business_income_loss_box_1": cb(
            r"Ordinary\s+business\s+income\s*\(?loss\)?"),
        "net_rental_real_estate_income_loss_box_2": cb(
            r"Net\s+rental\s+real\s+estate\s+income\s*\(?loss\)?"),
        "other_net_rental_income_loss_box_3": cb(
            r"Other\s+net\s+rental\s+income\s*\(?loss\)?"),
        "guaranteed_payments_services_box_4a": cb(
            r"Guaranteed\s+payments[^4\n]{0,10}[Ss]ervices"),
        "guaranteed_payments_capital_box_4b": cb(
            r"Guaranteed\s+payments[^4\n]{0,10}[Cc]apital"),
        "guaranteed_payments_total_box_4c": cb(
            r"Total\.\s+Add\s+lines\s+4a"),
        "interest_income_box_5": cb(r"Interest\s+income"),
        "ordinary_dividends_box_6a": cb(r"Ordinary\s+dividends"),
        "qualified_dividends_box_6b": cb(r"Qualified\s+dividends"),
        "royalties_box_7": cb(r"^Royalties"),
        "net_short_term_capital_gain_loss_box_8": cb(
            r"Net\s+short.?term\s+capital\s+gain"),
        "net_long_term_capital_gain_loss_box_9a": cb(
            r"Net\s+long.?term\s+capital\s+gain"),
        "collectibles_gain_loss_box_9b": cb(r"Collectibles\s*\(28"),
        "unrecaptured_sec1250_gain_box_9c": cb(r"Unrecaptured\s+section\s+1250"),
        "net_section_1231_gain_loss_box_10": cb(r"Net\s+section\s+1231"),
        "other_income_loss_box_11": cb(r"Other\s+income\s*\(?loss\)?"),
        "section_179_deduction_box_12": cb(r"Section\s+179\s+deduction"),
        "other_deductions_box_13": cb(r"Other\s+deductions"),
        "self_employment_earnings_loss_box_14": cb(
            r"Net\s+earnings\s*\(?loss\)?\s+from\s+self.?employment"),
        "credits_box_15": cb(r"Low.?income\s+housing\s+credit"),
        "distributions_box_19": cb(r"Distributions\s+of\s+cash\s+and\s+marketable"),
        "other_information_box_20": cb(r"Investment\s+income"),
    }


def _count_non_null(d: dict) -> int:
    return sum(1 for v in d.values() if v is not None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_k1_1065_from_text(text: str) -> dict[str, Any]:
    """Extract Schedule K-1 (Form 1065) fields from pre-extracted text.

    Accepts text obtained via pdfplumber or Tesseract OCR.
    """
    normalized = _normalize(text)
    result: dict[str, Any] = {}
    result.update(_extract_partnership_info(normalized))
    result.update(_extract_partner_info(normalized))
    result.update(_extract_boxes(normalized))
    result["tax_year"] = _extract_tax_year(normalized)
    return result


def extract_k1_1065_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract Schedule K-1 (Form 1065) or Schedule K fields from a digital PDF.

    Strategy (automatic):
      1. Text-flow regex  — works for standard K-1 slips where values are
         inline with their labels (most tax-software outputs).
      2. Coordinate-based — fallback for table-layout forms (e.g. Form 1065
         Page 4 / Schedule K) where values sit in a right-margin column and
         pdfplumber clusters them away from their labels in the text stream.
         Also handles integer-only amounts (no decimal point).
    The approach with more non-null box values wins.
    """
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("pdfplumber required. Run: pip install pdfplumber") from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(page.extract_text() or "" for page in pdf.pages)

    text_result = extract_k1_1065_from_text(raw)

    # Count how many box values the text approach found
    box_keys = [k for k in text_result if k not in (
        "partnership_ein", "partnership_name", "partner_tin",
        "partner_name", "ownership_percentage", "tax_year",
    )]
    text_hits = _count_non_null({k: text_result[k] for k in box_keys})

    # If text approach found fewer than 2 box values, try coordinate extraction.
    # Guard: only proceed if the right column contains real currency amounts
    # (comma-formatted like 7,350 or decimal like 62,000.00).  This prevents
    # false positives on blank templates whose right column only holds small
    # box-label integers (14, 15, 16…).
    if text_hits < 2:
        all_words, row_value_map = _build_coord_row_map(pdf_path)
        has_real_amounts = any(
            "," in w["text"] or "." in w["text"]
            for w in all_words
            if w["x0"] >= _VALUE_X_THRESHOLD and _parse_raw_amount(w["text"]) is not None
        )
        if not has_real_amounts:
            return text_result

        coord_boxes = _extract_boxes_by_coords(all_words, row_value_map)
        coord_hits = _count_non_null(coord_boxes)

        if coord_hits > text_hits:
            # Merge: keep header fields from text result, use coord box values
            text_result.update(coord_boxes)
            # Also attempt year extraction from raw text
            if text_result.get("tax_year") is None:
                yr = re.search(r"\b(20\d{2})\b", raw)
                text_result["tax_year"] = yr.group(1) if yr else None

    return text_result
