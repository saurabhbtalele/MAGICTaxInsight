"""Schedule C (Profit or Loss From Business) dedicated PDF extractor.

Replaces the generic regex-only entry in the registry with a
purpose-built parser covering Lines 1–31, business info, and
individual expense categories (Lines 8–27).
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
        return float(v.replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def _line_amount(
    line_num: int | str,
    label: str,
    text: str,
) -> float | None:
    """Extract ``<line_num> <label> <amount>`` from Schedule C text."""
    pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]{{2,}}\.\d{{2}})\)?"
    raw = _first(pattern, text)
    if not raw:
        pattern = rf"{line_num}\s+{label}.{0,150}?\s\(?([\d,]+)\)?"
        raw = _first(pattern, text)
    return _to_float(raw)


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract_schedule_c_fields(text: str) -> dict[str, Any]:
    """Core Schedule C extraction from normalised text."""
    return {
        # Business info
        "business_name": _first(
            r"(?:A|Name of proprietor)\s+(?:Principal\s+business)?"
            r"[^A-Z]{0,10}([A-Z][A-Za-z\s&.,'\-]{3,60})",
            text,
        ),
        "ein": _first(r"(?:D|EIN)\s*[:\s]+(\d{2}-\d{7})", text),
        "business_code": _first(
            r"(?:B|business\s+code)\s*[:\s]+(\d{6})", text
        ),
        "accounting_method": _first(
            r"(?:F|Accounting\s+method)\s*[:\s]+(Cash|Accrual|Other)",
            text,
        ),
        # Income
        "gross_receipts_line_1": _line_amount(
            1, r"Gross\s+receipts\s+or\s+sales", text
        ),
        "returns_allowances_line_2": _line_amount(
            2, r"Returns\s+and\s+allowances", text
        ),
        "cost_of_goods_sold_line_4": _line_amount(
            4, r"Cost\s+of\s+goods\s+sold", text
        ),
        "gross_income_line_7": _line_amount(7, r"Gross\s+income", text),
        # Expenses
        "advertising_line_8": _line_amount(8, r"Advertising", text),
        "car_truck_expenses_line_9": _line_amount(
            9, r"Car\s+and\s+truck\s+expenses", text
        ),
        "commissions_fees_line_10": _line_amount(
            10, r"Commissions\s+and\s+fees", text
        ),
        "contract_labor_line_11": _line_amount(
            11, r"Contract\s+labor", text
        ),
        "depletion_line_12": _line_amount(12, r"Depletion", text),
        "depreciation_line_13": _line_amount(
            13, r"Depreciation.*?179", text
        ),
        "employee_benefit_line_14": _line_amount(
            14, r"Employee\s+benefit", text
        ),
        "insurance_line_15": _line_amount(
            15, r"Insurance\s+\(other\s+than\s+health\)", text
        ),
        "interest_mortgage_line_16a": _line_amount(
            "16a", r"Mortgage.*?interest", text
        ),
        "interest_other_line_16b": _line_amount(
            "16b", r"Other\s+interest", text
        ),
        "legal_professional_line_17": _line_amount(
            17, r"Legal\s+and\s+professional", text
        ),
        "office_expense_line_18": _line_amount(
            18, r"Office\s+expense", text
        ),
        "pension_profit_sharing_line_19": _line_amount(
            19, r"Pension.*?plans", text
        ),
        "rent_lease_vehicles_line_20a": _line_amount(
            "20a", r"Rent.*?vehicles", text
        ),
        "rent_lease_other_line_20b": _line_amount(
            "20b", r"Rent.*?other\s+business", text
        ),
        "repairs_maintenance_line_21": _line_amount(
            21, r"Repairs\s+and\s+maintenance", text
        ),
        "supplies_line_22": _line_amount(22, r"Supplies", text),
        "taxes_licenses_line_23": _line_amount(
            23, r"Taxes\s+and\s+licenses", text
        ),
        "travel_line_24a": _line_amount(24, r"Travel", text),
        "meals_line_24b": _line_amount("24b", r"Meals", text),
        "utilities_line_25": _line_amount(25, r"Utilities", text),
        "wages_line_26": _line_amount(26, r"Wages", text),
        "other_expenses_line_27": _line_amount(
            27, r"Other\s+expenses", text
        ),
        # Totals
        "total_expenses_line_28": _line_amount(
            28, r"Total\s+expenses", text
        ),
        "tentative_profit_line_29": _line_amount(
            29, r"Tentative\s+profit", text
        ),
        "net_profit_loss_line_31": _line_amount(
            31, r"Net\s+profit\s+or", text
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_schedule_c_1040_from_text(text: str) -> dict[str, Any]:
    """Parse a full Schedule C (1040) text dump."""
    return _extract_schedule_c_fields(_normalize(text))


def extract_schedule_c_1040_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract Schedule C (1040) data directly from a digital PDF using pdfplumber.
    """
    import pdfplumber

    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_pages.append(page.extract_text() or "")
    
    raw = "\n".join(text_pages)
    return extract_schedule_c_1040_from_text(raw)
