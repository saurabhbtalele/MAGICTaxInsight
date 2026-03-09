"""Schedule F (Profit or Loss From Farming) PDF extractor.

Handles:
  Part I  — Farm Income (Cash Method): Lines 1a–11
  Part II — Farm Expenses: Lines 12–34
  Line 34: Total expenses
  Line 36: Net farm profit or loss
  Farm identity fields: name, EIN, accounting method, principal crop/activity
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


def _extract_schedule_f_fields(text: str) -> dict[str, Any]:
    """Core Schedule F extraction from normalised text."""
    return {
        # Farm identity
        "farm_name": _first(
            r"(?:Name\s+of\s+proprietor|principal\s+(?:crop|product))"
            r"[^A-Z]{0,10}([A-Z][A-Za-z\s&.,'\\-]{3,60})",
            text,
        ),
        "ein": _first(r"(?:D|EIN)\s*[:\s]+(\d{2}-\d{7})", text),
        "accounting_method": _first(
            r"(?:F|Accounting\s+method)\s*[:\s]+(Cash|Accrual|Other)", text
        ),
        "principal_crop_or_activity": _first(
            r"(?:B|Principal\s+(?:crop|product|activity))"
            r"[^A-Z]{0,10}([A-Z][A-Za-z\s&.,'-]{2,40})",
            text,
        ),
        # Part I — Farm Income (Cash Method)
        "sales_livestock_raised_line_1a": _line_amount(
            "1a", r"Sales\s+of\s+livestock.*?raised", text
        ),
        "cost_livestock_line_1b": _line_amount(
            "1b", r"Cost.*?basis.*?livestock", text
        ),
        "sales_livestock_bought_line_2": _line_amount(
            2, r"Sales\s+of\s+livestock.*?bought", text
        ),
        "ccc_loans_line_3a": _line_amount(
            "3a", r"Cooperative\s+distributions|CCC\s+loans", text
        ),
        "ag_program_payments_line_4a": _line_amount(
            "4a", r"Agricultural\s+program\s+payments", text
        ),
        "crop_insurance_line_6a": _line_amount(
            "6a", r"Crop\s+insurance\s+proceeds", text
        ),
        "custom_hire_income_line_7": _line_amount(
            7, r"Custom\s+hire.*?income", text
        ),
        "other_income_line_8": _line_amount(8, r"Other.*?income", text),
        "gross_income_line_9": _line_amount(
            9, r"Gross\s+(?:farm\s+)?income", text
        ),
        # Part II — Farm Expenses
        "car_truck_line_12": _line_amount(12, r"Car\s+and\s+truck", text),
        "chemicals_line_13": _line_amount(13, r"Chemicals", text),
        "conservation_line_14": _line_amount(14, r"Conservation", text),
        "custom_hire_line_15": _line_amount(
            15, r"Custom\s+hire.*?work", text
        ),
        "depreciation_line_16": _line_amount(16, r"Depreciation", text),
        "employee_benefit_line_17": _line_amount(
            17, r"Employee\s+benefit", text
        ),
        "feed_line_18": _line_amount(18, r"Feed", text),
        "fertilizers_line_19": _line_amount(
            19, r"Fertilizers\s+and\s+lime", text
        ),
        "freight_line_20": _line_amount(20, r"Freight\s+and\s+trucking", text),
        "gasoline_fuel_line_21": _line_amount(
            21, r"Gasoline.*?fuel.*?oil", text
        ),
        "insurance_line_22": _line_amount(22, r"Insurance", text),
        "interest_mortgage_line_23a": _line_amount(
            "23a", r"Mortgage.*?interest", text
        ),
        "interest_other_line_23b": _line_amount(
            "23b", r"Other.*?interest", text
        ),
        "labor_hired_line_24": _line_amount(24, r"Labor\s+hired", text),
        "pension_plans_line_25": _line_amount(25, r"Pension.*?plans", text),
        "rent_lease_vehicles_line_26a": _line_amount(
            "26a", r"Rent.*?vehicles", text
        ),
        "rent_lease_other_line_26b": _line_amount(
            "26b", r"Rent.*?other.*?property", text
        ),
        "repairs_maintenance_line_27": _line_amount(
            27, r"Repairs\s+and\s+maintenance", text
        ),
        "seeds_plants_line_28": _line_amount(
            28, r"Seeds\s+and\s+plants", text
        ),
        "storage_line_29": _line_amount(
            29, r"Storage\s+and\s+warehousing", text
        ),
        "supplies_line_30": _line_amount(30, r"Supplies", text),
        "taxes_line_31": _line_amount(31, r"Taxes", text),
        "utilities_line_32": _line_amount(32, r"Utilities", text),
        "vet_fees_line_33": _line_amount(
            33, r"Veterinary.*?(?:fees|breeding|medicine)", text
        ),
        "other_expenses_line_34": _line_amount(
            34, r"Other\s+(?:farm\s+)?expenses", text
        ),
        # Totals
        "total_expenses_line_35": _line_amount(
            35, r"Total\s+expenses", text
        ),
        "net_farm_profit_loss_line_36": _line_amount(
            36, r"Net\s+farm\s+profit.*?loss", text
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_schedule_f_1040_from_text(text: str) -> dict[str, Any]:
    """Parse a full Schedule F (1040) text dump."""
    return _extract_schedule_f_fields(_normalize(text))


def extract_schedule_f_1040_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract Schedule F (1040) data directly from a digital PDF using pdfplumber.
    """
    import pdfplumber

    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_pages.append(page.extract_text() or "")
    
    raw = "\n".join(text_pages)
    return extract_schedule_f_1040_from_text(raw)
