"""Form 1120-S (U.S. Income Tax Return for an S Corporation) PDF extractor.

Handles:
  Income: Lines 1a–6
  Deductions: Lines 7–21
  Schedule K: Lines 1–16d (income/loss items passed through to shareholders)
  Tax and Payments: Lines 22–27
  Corporation identity: name, EIN, address, etc.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.utils.pdf_utils import extract_interleaved_elements


# ---------------------------------------------------------------------------
# Coordinate-aware extraction helpers
# ---------------------------------------------------------------------------

def _find_value_near(elements: list[dict[str, Any]], label_pattern: str, max_dist_y: float = 15.0, max_dist_x: float = 400.0) -> str | None:
    """Finds a 'value' element physically near a label matching the pattern."""
    label_indices = []
    for i, e in enumerate(elements):
        if e['type'] == 'text' and re.search(label_pattern, e['text'], re.IGNORECASE):
            label_indices.append(i)
    
    if not label_indices:
        return None

    best_val = None
    min_dist = float('inf')

    # Values to ignore (interactive form artifacts)
    IGNORE_VALS = {'/Off', '/On', 'Off', 'On', '/', "/'Off'", "/'On'"}

    for idx in label_indices:
        l = elements[idx]
        for e in elements:
            if e['type'] != 'value':
                continue
            
            raw_text = e['text'].strip()
            # aggressive cleanup of [[VAL:...]] or '...' or "..."
            val_text = re.sub(r'^\[\[VAL:(.*)\]\]$', r'\1', raw_text)
            val_text = val_text.strip("'\" ").strip()
            
            if not val_text or val_text in IGNORE_VALS:
                continue

            dy = abs(e['top'] - l['top'])
            # Prefer values strictly to the right or slightly below/after
            dx = e['x0'] - l['x0'] 

            # Refined constraints: mostly same line or strictly to the right
            if dy <= max_dist_y and dx >= -5 and dx <= max_dist_x:
                # Euclidean-ish distance with heavy weight on vertical alignment
                # Prefer "same row" (dy near 0)
                dist = (dy * 10) + abs(dx) 
                if dist < min_dist:
                    min_dist = dist
                    best_val = val_text
            
    return best_val


def _line_amount_structured(elements: list[dict[str, Any]], line_num: str | int, label: str) -> float | None:
    # Try exact line number box ^NUM$
    anchor = rf"^{line_num}$"
    val = _find_value_near(elements, anchor, max_dist_y=10.0, max_dist_x=500.0)
    
    if not val:
        # Fallback to label text
        val = _find_value_near(elements, label, max_dist_y=15.0)
        
    return _to_float(val)


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        # Handle IRS style negatives (1,234.56) or -1234.56 or [[VAL:...]] artifacts
        cleaned = v.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip()
        # Remove any lingering VAL tags if they leaked in
        cleaned = re.sub(r'\[\[VAL:|\]\]', '', cleaned)
        if not cleaned or cleaned == "-":
            return None
        return float(cleaned)
    except ValueError:
        return None


def _to_int(v: str | None) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _extract_1120s_elements(elements: list[dict[str, Any]]) -> dict[str, Any]:
    """Exhaustive extraction using page coordinates."""
    
    def _v(pat: str, dy: float = 15.0, dx: float = 400.0):
        return _find_value_near(elements, pat, dy, dx)

    def _f(line: str | int, label: str):
        return _line_amount_structured(elements, line, label)

    return {
        # Identity (Box A-I)
        "ein": _v(r"Employer\s+identification") or _v(r"EIN"),
        "corporation_name": _v(r"^Name$", dy=10.0),
        "address": _v(r"Number\s+and\s+street"),
        "city": _v(r"City\s+or\s+town"),
        "state": _v(r"State\s+or\s+province"),
        "zip": _v(r"ZIP\s+or\s+foreign"),
        "s_election_date": _v(r"A\s+S\s+election"),
        "business_activity_code": _v(r"B\s+Business\s+activity"),
        "date_incorporated": _v(r"E\s+Date\s+incorporated"),
        "total_assets": _to_float(_v(r"F\s+Total\s+assets")),
        "number_of_shareholders": _to_int(_v(r"I\s+Enter\s+the\s+number")),

        # Page 1 Income
        "gross_receipts_line_1a": _f("1a", r"Gross\s+receipts"),
        "returns_allowances_line_1b": _f("1b", r"Less\s+returns"),
        "cost_of_goods_sold_line_2": _f(2, r"Cost\s+of\s+goods\s+sold"),
        "gross_profit_line_3": _f(3, r"Gross\s+profit"),
        "net_gain_loss_line_4": _f(4, r"Net\s+gain"),
        "other_income_line_5": _f(5, r"Other\s+income"),
        "total_income_line_6": _f(6, r"Total\s+income"),

        # Page 1 Deductions
        "compensation_officers_line_7": _f(7, r"Compensation\s+of\s+officers"),
        "salaries_wages_line_8": _f(8, r"Salaries\s+and\s+wages"),
        "repairs_maintenance_line_9": _f(9, r"Repairs\s+and\s+maintenance"),
        "bad_debts_line_10": _f(10, r"Bad\s+debts"),
        "rents_line_11": _f(11, r"Rents"),
        "taxes_licenses_line_12": _f(12, r"Taxes\s+and\s+licenses"),
        "interest_line_13": _f(13, r"Interest"),
        "depreciation_line_14": _f(14, r"Depreciation"),
        "depletion_line_15": _f(15, r"Depletion"),
        "advertising_line_16": _f(16, r"Advertising"),
        "pension_plans_line_17": _f(17, r"Pension.*?plans"),
        "employee_benefit_line_18": _f(18, r"Employee\s+benefit"),
        "energy_deduction_line_19": _f(19, r"Energy\s+efficient"),
        "other_deductions_line_20": _f(20, r"Other\s+deductions"),
        "total_deductions_line_21": _f(21, r"Total\s+deductions"),

        # Page 1 Totals & Tax
        "ordinary_business_income_loss_line_22": _f(22, r"Ordinary\s+business\s+income"),
        "excess_passive_tax_line_23a": _f("23a", r"Excess\s+net\s+passive"),
        "schedule_d_tax_line_23b": _f("23b", r"Tax\s+from\s+Schedule\s+D"),
        "total_tax_line_23c": _f("23c", r"Add\s+lines\s+23a\s+and\s+23b"),
        "estimated_tax_payments_line_24a": _f("24a", r"Current\s+year’s\s+estimated"),
        "tax_deposited_7004_line_24b": _f("24b", r"Tax\s+deposited\s+with\s+Form\s+7004"),
        "fuel_tax_credit_line_24c": _f("24c", r"Credit\s+for\s+federal\s+tax"),
        "total_payments_line_24z": _f("24z", r"Add\s+lines\s+24a\s+through\s+24d"),
        "estimated_tax_penalty_line_25": _f(25, r"Estimated\s+tax\s+penalty"),
        "amount_owed_line_26": _f(26, r"Amount\s+owed"),
        "overpayment_line_27": _f(27, r"Overpayment"),

        # Schedule K (Page 3)
        "k_ordinary_income_line_1": _f(1, r"Ordinary\s+business\s+income.*?Schedule\s+K"),
        "k_rental_income_line_2": _f(2, r"Net\s+rental\s+real\s+estate.*?Schedule\s+K"),
        "k_interest_income_line_4": _f(4, r"Interest\s+income.*?Schedule\s+K"),
        "k_ordinary_dividends_line_5a": _f("5a", r"Ordinary\s+dividends.*?Schedule\s+K"),
        "k_qualified_dividends_line_5b": _f("5b", r"Qualified\s+dividends.*?Schedule\s+K"),
        "k_royalties_line_6": _f(6, r"Royalties.*?Schedule\s+K"),
        "k_net_short_term_gain_line_7": _f(7, r"Net\s+short-term.*?Schedule\s+K"),
        "k_net_long_term_gain_line_8a": _f("8a", r"Net\s+long-term.*?Schedule\s+K"),
        "k_section_179_deduction_line_11": _f(11, r"Section\s+179.*?Schedule\s+K"),
        "k_distributions_line_16d": _f("16d", r"Distributions.*?Schedule\s+K"),

        # Schedule B (Page 2)
        "sch_b_q1a_yes": _v(r"1a"),
        "sch_b_q1a_no": None,
        "sch_b_q1b_yes": _v(r"1b"),
        "sch_b_q1b_no": None,
        "sch_b_q2_yes": _v(r"2 Own directly"),
        "sch_b_q2_no": None,
        "sch_b_q3_yes": _v(r"3"),
        "sch_b_q3_no": None,
        "sch_b_q4a_yes": _v(r"4a"),
        "sch_b_q4a_no": None,
        "sch_b_q4b_yes": _v(r"4b"),
        "sch_b_q4b_no": None,
        "sch_b_q5a_yes": _v(r"5a"),
        "sch_b_q5a_no": None,
        "sch_b_q5a_i": _to_int(_v(r"Total shares of restricted stock")),
        "sch_b_q5a_ii": _to_int(_v(r"Total shares of non-restricted stock")),
        "sch_b_q5b_yes": _v(r"5b"),
        "sch_b_q5b_no": None,
        "sch_b_q5b_i": _to_int(_v(r"Total shares of stock outstanding.*tax year")),
        "sch_b_q5b_ii": _to_int(_v(r"Total shares of stock outstanding if all")),
        "sch_b_q6_yes": _v(r"6 Has this corporation"),
        "sch_b_q6_no": None,
        "sch_b_q7_checkbox": None,
        "sch_b_q8_yes": _v(r"8 If the corporation"),
        "sch_b_q8_no": None,
        "sch_b_q8_amount": _to_float(_v(r"8 If the corporation")),
        "sch_b_q9_yes": _v(r"9 Did the corporation have an election under section 163"),
        "sch_b_q9_no": None,
        "sch_b_q10_yes": _v(r"10 Does the corporation satisfy"),
        "sch_b_q10_no": None,
        "sch_b_q11_yes": _v(r"11 Does the corporation satisfy both"),
        "sch_b_q11_no": None,

        # Schedule K Continued
        "k_investment_income_line_17a": _f("17a", r"Investment\s+income"),
        "k_investment_expenses_line_17b": _f("17b", r"Investment\s+expenses"),
        "k_dividend_distributions_line_17c": _f("17c", r"Dividend\s+distributions"),
        "k_other_items_line_17d": _f("17d", r"Other\s+items\s+and\s+amounts"),
        "k_income_reconciliation_line_18": _f(18, r"Income\s+\(loss\)\s+reconciliation"),

        # Schedule L (Balance Sheets)
        "sch_l_cash_line_1_begin": _f(1, r"1\s+Cash"),
        "sch_l_cash_line_1_end": None,
        "sch_l_trade_notes_line_2a_begin": _f("2a", r"Trade\s+notes\s+and\s+accounts\s+receivable"),
        "sch_l_trade_notes_line_2a_end": None,
        "sch_l_bad_debts_allowance_line_2b_begin": _f("b", r"Less\s+allowance\s+for\s+bad\s+debts"),
        "sch_l_bad_debts_allowance_line_2b_end": None,
        "sch_l_inventories_line_3_begin": _f(3, r"Inventories"),
        "sch_l_inventories_line_3_end": None,
        "sch_l_us_gov_obligations_line_4_begin": _f(4, r"U\.S\.\s+government\s+obligations"),
        "sch_l_us_gov_obligations_line_4_end": None,
        "sch_l_tax_exempt_securities_line_5_begin": _f(5, r"Tax-exempt\s+securities"),
        "sch_l_tax_exempt_securities_line_5_end": None,
        "sch_l_other_current_assets_line_6_begin": _f(6, r"Other\s+current\s+assets"),
        "sch_l_other_current_assets_line_6_end": None,
        "sch_l_loans_to_shareholders_line_7_begin": _f(7, r"Loans\s+to\s+shareholders"),
        "sch_l_loans_to_shareholders_line_7_end": None,
        "sch_l_mortgage_real_estate_loans_line_8_begin": _f(8, r"Mortgage\s+and\s+real\s+estate\s+loans"),
        "sch_l_mortgage_real_estate_loans_line_8_end": None,
        "sch_l_other_investments_line_9_begin": _f(9, r"Other\s+investments"),
        "sch_l_other_investments_line_9_end": None,
        "sch_l_buildings_depreciable_assets_line_10a_begin": _f("10a", r"Buildings\s+and\s+other\s+depreciable"),
        "sch_l_buildings_depreciable_assets_line_10a_end": None,
        "sch_l_accumulated_depreciation_line_10b_begin": _f("b", r"Less\s+accumulated\s+depreciation"),
        "sch_l_accumulated_depreciation_line_10b_end": None,
        "sch_l_depletable_assets_line_11a_begin": _f("11a", r"Depletable\s+assets"),
        "sch_l_depletable_assets_line_11a_end": None,
        "sch_l_accumulated_depletion_line_11b_begin": _f("b", r"Less\s+accumulated\s+depletion"),
        "sch_l_accumulated_depletion_line_11b_end": None,
        "sch_l_land_line_12_begin": _f(12, r"Land"),
        "sch_l_land_line_12_end": None,
        "sch_l_intangible_assets_line_13a_begin": _f("13a", r"Intangible\s+assets"),
        "sch_l_intangible_assets_line_13a_end": None,
        "sch_l_accumulated_amortization_line_13b_begin": _f("b", r"Less\s+accumulated\s+amortization"),
        "sch_l_accumulated_amortization_line_13b_end": None,
        "sch_l_other_assets_line_14_begin": _f(14, r"Other\s+assets"),
        "sch_l_other_assets_line_14_end": None,
        "sch_l_total_assets_line_15_begin": _f(15, r"Total\s+assets"),
        "sch_l_total_assets_line_15_end": None,
        "sch_l_accounts_payable_line_16_begin": _f(16, r"Accounts\s+payable"),
        "sch_l_accounts_payable_line_16_end": None,
        "sch_l_mortgages_notes_under_1yr_line_17_begin": _f(17, r"Mortgages,\s+notes,\s+bonds\s+payable\s+in\s+less\s+than\s+1\s+year"),
        "sch_l_mortgages_notes_under_1yr_line_17_end": None,
        "sch_l_other_current_liabilities_line_18_begin": _f(18, r"Other\s+current\s+liabilities"),
        "sch_l_other_current_liabilities_line_18_end": None,
        "sch_l_loans_from_shareholders_line_19_begin": _f(19, r"Loans\s+from\s+shareholders"),
        "sch_l_loans_from_shareholders_line_19_end": None,
        "sch_l_mortgages_notes_over_1yr_line_20_begin": _f(20, r"Mortgages,\s+notes,\s+bonds\s+payable\s+in\s+1\s+year\s+or\s+more"),
        "sch_l_mortgages_notes_over_1yr_line_20_end": None,
        "sch_l_other_liabilities_line_21_begin": _f(21, r"Other\s+liabilities"),
        "sch_l_other_liabilities_line_21_end": None,
        "sch_l_capital_stock_line_22_begin": _f(22, r"Capital\s+stock"),
        "sch_l_capital_stock_line_22_end": None,
        "sch_l_additional_paid_in_capital_line_23_begin": _f(23, r"Additional\s+paid-in\s+capital"),
        "sch_l_additional_paid_in_capital_line_23_end": None,
        "sch_l_retained_earnings_line_24_begin": _f(24, r"Retained\s+earnings"),
        "sch_l_retained_earnings_line_24_end": None,
        "sch_l_adjustments_to_equity_line_25_begin": _f(25, r"Adjustments\s+to\s+shareholders'\s+equity"),
        "sch_l_adjustments_to_equity_line_25_end": None,
        "sch_l_less_cost_treasury_stock_line_26_begin": _f(26, r"Less\s+cost\s+of\s+treasury\s+stock"),
        "sch_l_less_cost_treasury_stock_line_26_end": None,
        "sch_l_total_liabilities_equity_line_27_begin": _f(27, r"Total\s+liabilities\s+and\s+shareholders'\s+equity"),
        "sch_l_total_liabilities_equity_line_27_end": None,

        # Schedule M-1 (Page 5)
        "sch_m1_net_income_books_line_1": _f(1, r"Net\s+income\s+\(loss\)\s+per\s+books"),
        "sch_m1_income_on_k_not_books_line_2": _f(2, r"Income\s+included\s+on\s+Schedule\s+K"),
        "sch_m1_expenses_books_not_k_line_3": _f(3, r"Expenses\s+recorded\s+on\s+books"),
        "sch_m1_depreciation_line_3a": _f("a", r"Depreciation"), # Needs stricter anchor in reality
        "sch_m1_travel_entertainment_line_3b": _f("b", r"Travel\s+and\s+entertainment"),
        "sch_m1_add_lines_1_to_3_line_4": _f(4, r"Add\s+lines\s+1\s+through\s+3"),
        "sch_m1_income_books_not_k_line_5": _f(5, r"Income\s+recorded\s+on\s+books"),
        "sch_m1_tax_exempt_interest_line_5a": _f("a", r"Tax-exempt\s+interest"),
        "sch_m1_deductions_k_not_books_line_6": _f(6, r"Deductions\s+included\s+on\s+Schedule\s+K"),
        "sch_m1_depreciation_line_6a": _f("a", r"Depreciation"),
        "sch_m1_add_lines_5_and_6_line_7": _f(7, r"Add\s+lines\s+5\s+and\s+6"),
        "sch_m1_income_reconciliation_line_8": _f(8, r"Income\s+\(loss\)\s+\(Schedule\s+K,\s+line\s+18\)"),

        # Schedule M-2 (Page 5)
        "sch_m2_balance_beginning_line_1_col_a": _f(1, r"Balance\s+at\s+beginning\s+of\s+tax\s+year"),
        "sch_m2_balance_beginning_line_1_col_b": None,
        "sch_m2_balance_beginning_line_1_col_c": None,
        "sch_m2_balance_beginning_line_1_col_d": None,
        "sch_m2_ordinary_income_line_2_col_a": _f(2, r"Ordinary\s+income\s+from\s+page\s+1"),
        "sch_m2_ordinary_income_line_2_col_b": None,
        "sch_m2_ordinary_income_line_2_col_c": None,
        "sch_m2_ordinary_income_line_2_col_d": None,
        "sch_m2_other_additions_line_3_col_a": _f(3, r"Other\s+additions"),
        "sch_m2_other_additions_line_3_col_b": None,
        "sch_m2_other_additions_line_3_col_c": None,
        "sch_m2_other_additions_line_3_col_d": None,
        "sch_m2_loss_line_4_col_a": _f(4, r"Loss\s+from\s+page\s+1"),
        "sch_m2_loss_line_4_col_b": None,
        "sch_m2_loss_line_4_col_c": None,
        "sch_m2_loss_line_4_col_d": None,
        "sch_m2_other_reductions_line_5_col_a": _f(5, r"Other\s+reductions"),
        "sch_m2_other_reductions_line_5_col_b": None,
        "sch_m2_other_reductions_line_5_col_c": None,
        "sch_m2_other_reductions_line_5_col_d": None,
        "sch_m2_combine_line_6_col_a": _f(6, r"Combine\s+lines\s+1\s+through\s+5"),
        "sch_m2_combine_line_6_col_b": None,
        "sch_m2_combine_line_6_col_c": None,
        "sch_m2_combine_line_6_col_d": None,
        "sch_m2_distributions_line_7_col_a": _f(7, r"Distributions"),
        "sch_m2_distributions_line_7_col_b": None,
        "sch_m2_distributions_line_7_col_c": None,
        "sch_m2_distributions_line_7_col_d": None,
        "sch_m2_balance_end_line_8_col_a": _f(8, r"Balance\s+at\s+end\s+of\s+tax\s+year"),
        "sch_m2_balance_end_line_8_col_b": None,
        "sch_m2_balance_end_line_8_col_c": None,
        "sch_m2_balance_end_line_8_col_d": None,
    }


def extract_1120s_from_text(text: str) -> dict[str, Any]:
    """Fallback - not used in coord mode."""
    return {}


def extract_1120s_from_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Main entry point: extracts Form 1120-S fields using element coordinates."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber required") from exc

    all_elements = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            all_elements.extend(extract_interleaved_elements(page))

    return _extract_1120s_elements(all_elements)
