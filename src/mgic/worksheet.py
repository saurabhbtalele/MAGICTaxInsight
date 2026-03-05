"""MGIC SAM Cash Flow Analysis Worksheet — Phase 1 subset.

Covers:
  W-2      Boxes 1-6  (wages, SS wages/tax, Medicare wages/tax, fed withheld)
  1099-NEC Box 1      (nonemployee compensation)
  1099-R   Box 1/2a   (gross distribution, taxable amount)
  Schedule C Line 31  (net profit/loss from sole proprietorship)
  Form 1040 Lines 1/11/15/24 (wages, AGI, taxable income, total tax)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from src.models.document import ExtractedForm


@dataclass
class MgicRow:
    row_id: str
    label: str
    source: str
    value: float | None


def _f(form: ExtractedForm, name: str) -> float | None:
    """Safely coerce an extracted field to float."""
    raw = form.fields.get(name)
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _w2_rows(form: ExtractedForm) -> List[MgicRow]:
    return [
        MgicRow("W2_01", "W-2 Box 1  — Wages, tips, other compensation",       "W-2", _f(form, "wages_tips_other_compensation_box_1")),
        MgicRow("W2_02", "W-2 Box 2  — Federal income tax withheld",            "W-2", _f(form, "federal_income_tax_withheld_box_2")),
        MgicRow("W2_03", "W-2 Box 3  — Social security wages",                  "W-2", _f(form, "social_security_wages_box_3")),
        MgicRow("W2_04", "W-2 Box 4  — Social security tax withheld",           "W-2", _f(form, "social_security_tax_withheld_box_4")),
        MgicRow("W2_05", "W-2 Box 5  — Medicare wages and tips",                "W-2", _f(form, "medicare_wages_tips_box_5")),
        MgicRow("W2_06", "W-2 Box 6  — Medicare tax withheld",                  "W-2", _f(form, "medicare_tax_withheld_box_6")),
    ]


def _nec_rows(form: ExtractedForm) -> List[MgicRow]:
    return [
        MgicRow("NEC_01", "1099-NEC Box 1 — Nonemployee compensation",          "1099-NEC", _f(form, "nonemployee_compensation_box_1")),
        MgicRow("NEC_04", "1099-NEC Box 4 — Federal income tax withheld",       "1099-NEC", _f(form, "federal_income_tax_withheld_box_4")),
    ]


def _1099r_rows(form: ExtractedForm) -> List[MgicRow]:
    return [
        MgicRow("R_01",  "1099-R Box 1  — Gross distribution",                 "1099-R", _f(form, "gross_distribution_box_1")),
        MgicRow("R_02a", "1099-R Box 2a — Taxable amount",                     "1099-R", _f(form, "taxable_amount_box_2a")),
        MgicRow("R_04",  "1099-R Box 4  — Federal income tax withheld",        "1099-R", _f(form, "federal_income_tax_withheld_box_4")),
    ]


def _schedule_c_rows(form: ExtractedForm) -> List[MgicRow]:
    return [
        MgicRow("SC_01", "Sched C Line 1  — Gross receipts",                   "Schedule C", _f(form, "gross_receipts_line_1")),
        MgicRow("SC_07", "Sched C Line 7  — Gross income",                     "Schedule C", _f(form, "gross_income_line_7")),
        MgicRow("SC_28", "Sched C Line 28 — Total expenses",                   "Schedule C", _f(form, "total_expenses_line_28")),
        MgicRow("SC_31", "Sched C Line 31 — Net profit (loss)",                "Schedule C", _f(form, "net_profit_or_loss_line_31")),
    ]


def _form1040_rows(form: ExtractedForm) -> List[MgicRow]:
    return [
        MgicRow("F1040_01", "1040 Line 1  — Wages, salaries, tips",            "1040", _f(form, "wages_salaries_tips_line_1")),
        MgicRow("F1040_11", "1040 Line 11 — Adjusted gross income (AGI)",      "1040", _f(form, "adjusted_gross_income_line_11")),
        MgicRow("F1040_15", "1040 Line 15 — Taxable income",                   "1040", _f(form, "taxable_income_line_15")),
        MgicRow("F1040_24", "1040 Line 24 — Total tax",                        "1040", _f(form, "total_tax_line_24")),
        MgicRow("F1040_25", "1040 Line 25 — Federal income tax withheld",      "1040", _f(form, "federal_tax_withheld_line_25")),
        MgicRow("F1040_34", "1040 Line 34 — Refund amount",                    "1040", _f(form, "amount_refunded_line_34")),
        MgicRow("F1040_37", "1040 Line 37 — Amount owed",                      "1040", _f(form, "amount_owed_line_37")),
    ]


_FORM_HANDLERS = {
    "W-2":        _w2_rows,
    "1099-NEC":   _nec_rows,
    "1099-R":     _1099r_rows,
    "Schedule C": _schedule_c_rows,
    "1040":       _form1040_rows,
}


def build_mgic_worksheet(forms: List[ExtractedForm]) -> Dict[str, Any]:
    """Build the MGIC cash-flow worksheet from all extracted forms."""
    rows: List[MgicRow] = []

    for form in forms:
        handler = _FORM_HANDLERS.get(form.form_id)
        if handler:
            rows.extend(handler(form))

    def _sum(prefix: str) -> float:
        return sum(r.value or 0.0 for r in rows if r.row_id.startswith(prefix))

    return {
        "rows": [asdict(r) for r in rows],
        "totals": {
            "w2_wages_box1":                    _sum("W2_01"),
            "w2_federal_tax_withheld_box2":     _sum("W2_02"),
            "w2_ss_wages_box3":                 _sum("W2_03"),
            "w2_ss_tax_box4":                   _sum("W2_04"),
            "w2_medicare_wages_box5":           _sum("W2_05"),
            "w2_medicare_tax_box6":             _sum("W2_06"),
            "nec_income_total":                 _sum("NEC_01"),
            "retirement_gross_distribution":    _sum("R_01"),
            "retirement_taxable_amount":        _sum("R_02a"),
            "schedule_c_net_profit":            _sum("SC_31"),
            "form1040_agi":                     _sum("F1040_11"),
            "form1040_total_tax":               _sum("F1040_24"),
        },
    }
