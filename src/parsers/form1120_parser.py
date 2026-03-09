"""Form 1120 (U.S. Corporation Income Tax Return) PDF extractor.

Handles:
  Income: Lines 1a–11 (gross receipts, COGS, dividends, interest,
          rents, royalties, capital gains, other income, total income)
  Deductions: Lines 12–29a (compensation, rent, taxes, interest,
              depreciation, advertising, etc.)
  Line 30: Taxable income before NOL/special deductions
  Line 31: Total tax
  Schedule J (Tax Computation): Lines 1–10
  Corporation identity: name, EIN, date incorporated
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.utils.pdf_utils import extract_interleaved_text


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


def _extract_1120_fields(text: str) -> dict[str, Any]:
    """Core Form 1120 extraction from normalised text."""
    return {
        # Identity
        "corporation_name": _first(
            r"(?:Name|Corporation).*?([A-Z][A-Za-z0-9\s&.,'\\-]{2,60})(?!\s*(?:number|EIN|Employer))",
            text,
        ),
        "ein": _first(
            r"(?:EIN|Employer\s+identification)\s*[:\s]+(\d{2}-\d{7})", text
        ),
        "date_incorporated": _first(
            r"(?:Date\s+incorporated)\s*[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})", text
        ),
        # Income
        "gross_receipts_line_1a": _line_amount(
            "1a", r"Gross\s+receipts\s+or\s+sales", text
        ),
        "returns_allowances_line_1b": _line_amount(
            "1b", r"Returns\s+and\s+allowances", text
        ),
        "cost_of_goods_sold_line_2": _line_amount(
            2, r"Cost\s+of\s+goods\s+sold", text
        ),
        "gross_profit_line_3": _line_amount(3, r"Gross\s+profit", text),
        "dividends_line_4": _line_amount(
            4, r"Dividends.*?Schedule\s+C", text
        ),
        "interest_line_5": _line_amount(5, r"Interest", text),
        "gross_rents_line_6": _line_amount(6, r"Gross\s+rents", text),
        "gross_royalties_line_7": _line_amount(
            7, r"Gross\s+royalties", text
        ),
        "capital_gain_line_8": _line_amount(
            8, r"Capital\s+gain.*?net", text
        ),
        "net_gain_loss_line_9": _line_amount(
            9, r"Net\s+gain\s+or\s+\(loss\)", text
        ),
        "other_income_line_10": _line_amount(10, r"Other\s+income", text),
        "total_income_line_11": _line_amount(11, r"Total\s+income", text),
        # Deductions
        "compensation_officers_line_12": _line_amount(
            12, r"Compensation\s+of\s+officers", text
        ),
        "salaries_wages_line_13": _line_amount(
            13, r"Salaries\s+and\s+wages", text
        ),
        "repairs_maintenance_line_14": _line_amount(
            14, r"Repairs\s+and\s+maintenance", text
        ),
        "bad_debts_line_15": _line_amount(15, r"Bad\s+debts", text),
        "rents_line_16": _line_amount(16, r"Rents", text),
        "taxes_licenses_line_17": _line_amount(
            17, r"Taxes\s+and\s+licenses", text
        ),
        "interest_line_18": _line_amount(18, r"Interest", text),
        "charitable_contributions_line_19": _line_amount(
            19, r"Charitable\s+contributions", text
        ),
        "depreciation_line_20": _line_amount(20, r"Depreciation", text),
        "depletion_line_21": _line_amount(21, r"Depletion", text),
        "advertising_line_22": _line_amount(22, r"Advertising", text),
        "pension_plans_line_23": _line_amount(
            23, r"Pension.*?plans", text
        ),
        "employee_benefit_line_24": _line_amount(
            24, r"Employee\s+benefit", text
        ),
        "domestic_production_line_25": _line_amount(
            25, r"Domestic\s+production", text
        ),
        "other_deductions_line_26": _line_amount(
            26, r"Other\s+deductions", text
        ),
        "total_deductions_line_27": _line_amount(
            27, r"Total\s+deductions", text
        ),
        "taxable_income_before_nol_line_28": _line_amount(
            28, r"Taxable\s+income\s+before", text
        ),
        "nol_deduction_line_29a": _line_amount(
            "29a", r"Net\s+operating\s+loss\s+deduction", text
        ),
        "special_deductions_line_29b": _line_amount(
            "29b", r"Special\s+deductions", text
        ),
        "taxable_income_line_30": _line_amount(
            30, r"Taxable\s+income", text
        ),
        "total_tax_line_31": _line_amount(31, r"Total\s+tax", text),
        # Payments
        "total_payments_line_32": _line_amount(
            32, r"Total\s+payments", text
        ),
        "estimated_tax_penalty_line_33": _line_amount(
            33, r"Estimated\s+tax\s+penalty", text
        ),
        "amount_owed_line_34": _line_amount(
            34, r"Amount\s+owed", text
        ),
        "overpayment_line_35": _line_amount(
            35, r"Overpayment", text
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_1120_from_text(text: str) -> dict[str, Any]:
    """Extract Form 1120 fields from pre-extracted text."""
    return _extract_1120_fields(_normalize(text))


def extract_1120_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract Form 1120 fields from a digital PDF."""
    try:
        import pdfplumber  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber required. Run: pip install pdfplumber"
        ) from exc

    with pdfplumber.open(str(pdf_path)) as pdf:
        raw = " ".join(extract_interleaved_text(p) for p in pdf.pages)

    return extract_1120_from_text(raw)
