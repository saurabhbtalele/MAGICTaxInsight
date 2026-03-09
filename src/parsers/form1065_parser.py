"""Form 1065 (U.S. Return of Partnership Income) PDF extractor.

Handles:
  Page 1 Income: Lines 1a–8
  Deductions: Lines 9–21
  Line 22: Ordinary business income/loss
  Schedule K Totals (aggregate distributive share items)
  Partnership identity: name, EIN, address, date started, accounting method
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
# Core extraction
# ---------------------------------------------------------------------------


def _extract_1065_fields(text: str) -> dict[str, Any]:
    """Core Form 1065 extraction from normalised text."""
    return {
        # Identity
        "partnership_name": _first(
            r"(?:Name\s+of\s+partnership|name)[^A-Z]{0,10}([A-Z][A-Za-z\s&.,'\\-]{3,60})",
            text,
        ),
        "ein": _first(r"(?:EIN|Employer\s+identification)\s*[:\s]+(\d{2}-\d{7})", text),
        "date_business_started": _first(
            r"(?:D|Date\s+business\s+started)\s*[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})", text
        ),
        "accounting_method": _first(
            r"(?:Accounting\s+method)\s*[:\s]+(Cash|Accrual|Other)", text
        ),
        "number_of_partners": _first(
            r"(?:number\s+of\s+Schedules\s+K-1|number\s+of\s+partners)\s*[:\s]+(\d+)", text
        ),
        # Income (Page 1)
        "gross_receipts_line_1a": _line_amount(
            "1a", r"Gross\s+receipts\s+or\s+sales", text
        ),
        "returns_allowances_line_1b": _line_amount(
            "1b", r"Returns\s+and\s+allowances", text
        ),
        "cost_of_goods_sold_line_2": _line_amount(
            2, r"Cost\s+of\s+goods\s+sold", text
        ),
        "gross_profit_line_3": _line_amount(
            3, r"Gross\s+profit", text
        ),
        "ordinary_income_other_partnerships_line_4": _line_amount(
            4, r"Ordinary\s+income.*?partnerships", text
        ),
        "net_farm_profit_loss_line_5": _line_amount(
            5, r"Net\s+farm\s+profit", text
        ),
        "net_gain_loss_line_6": _line_amount(
            6, r"Net\s+gain\s+\(loss\)", text
        ),
        "other_income_line_7": _line_amount(7, r"Other\s+income", text),
        "total_income_line_8": _line_amount(
            8, r"Total\s+income", text
        ),
        # Deductions
        "salaries_wages_line_9": _line_amount(
            9, r"Salaries\s+and\s+wages", text
        ),
        "guaranteed_payments_line_10": _line_amount(
            10, r"Guaranteed\s+payments\s+to\s+partners", text
        ),
        "repairs_maintenance_line_11": _line_amount(
            11, r"Repairs\s+and\s+maintenance", text
        ),
        "bad_debts_line_12": _line_amount(12, r"Bad\s+debts", text),
        "rent_line_13": _line_amount(13, r"Rent", text),
        "taxes_licenses_line_14": _line_amount(
            14, r"Taxes\s+and\s+licenses", text
        ),
        "interest_line_15": _line_amount(15, r"Interest", text),
        "depreciation_line_16a": _line_amount(
            "16a", r"Depreciation", text
        ),
        "depletion_line_17": _line_amount(17, r"Depletion", text),
        "retirement_plans_line_18": _line_amount(
            18, r"Retirement\s+plans", text
        ),
        "employee_benefit_line_19": _line_amount(
            19, r"Employee\s+benefit", text
        ),
        "other_deductions_line_20": _line_amount(
            20, r"Other\s+deductions", text
        ),
        "total_deductions_line_21": _line_amount(
            21, r"Total\s+deductions", text
        ),
        "ordinary_business_income_loss_line_22": _line_amount(
            22, r"Ordinary\s+business\s+income.*?loss", text
        ),
        # Schedule K summary items
        "schedule_k_ordinary_income_line_1": _line_amount(
            1, r"Ordinary\s+business\s+income.*?loss.*?Schedule\s+K", text
        ),
        "schedule_k_rental_income_line_2": _line_amount(
            2, r"Net\s+rental\s+real\s+estate.*?Schedule\s+K", text
        ),
        "schedule_k_guaranteed_payments_line_4c": _line_amount(
            "4c", r"Total\s+guaranteed\s+payments", text
        ),
        "schedule_k_interest_income_line_5": _line_amount(
            5, r"Interest\s+income.*?Schedule\s+K", text
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_1065_from_text(text: str) -> dict[str, Any]:
    """Extract Form 1065 fields from pre-extracted text."""
    return _extract_1065_fields(_normalize(text))


def extract_1065_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract Form 1065 fields from a digital PDF."""
    try:
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber required. Run: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(p.extract_text() or "" for p in pdf.pages)

    return extract_1065_from_text(raw)
