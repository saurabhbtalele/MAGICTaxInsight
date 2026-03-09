"""Unit tests for Phase B parsers: 1099-MISC, Schedule B, Schedule C."""

import pytest

from src.parsers.form1099misc_parser import extract_1099misc_from_text
from src.parsers.schedule_b_1040_parser import extract_schedule_b_1040_from_text
from src.parsers.schedule_c_1040_parser import extract_schedule_c_1040_from_text


# ---------------------------------------------------------------------------
# 1099-MISC
# ---------------------------------------------------------------------------

SAMPLE_1099MISC = """
PAYER'S TIN 12-3456789
RECIPIENT'S TIN 987-65-4321
RECIPIENT'S name John Doe
1 Rents 5,000.00
2 Royalties 1,200.50
3 Other income 750.00
4 Federal income tax withheld 500.00
5 Fishing boat proceeds 0.00
6 Medical and health care payments 3,200.00
7 Nonemployee compensation 15,000.00
8 Substitute payments 0.00
10 Crop insurance proceeds 0.00
13 Excess golden parachute 0.00
14 Gross proceeds to an attorney 2,500.00
"""


class Test1099MISC:
    def test_extracts_tins(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["payer_tin"] == "12-3456789"
        assert result["recipient_tin"] == "987-65-4321"

    def test_extracts_rents(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["rents_box_1"] == 5000.00

    def test_extracts_royalties(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["royalties_box_2"] == 1200.50

    def test_extracts_other_income(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["other_income_box_3"] == 750.00

    def test_extracts_fed_tax_withheld(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["federal_income_tax_withheld_box_4"] == 500.00

    def test_extracts_nonemployee_comp(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["nonemployee_compensation_box_7"] == 15000.00

    def test_extracts_medical_payments(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["medical_payments_box_6"] == 3200.00

    def test_extracts_attorney_proceeds(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["gross_proceeds_attorney_box_14"] == 2500.00

    def test_missing_fields_return_none(self):
        result = extract_1099misc_from_text("Some random text with no 1099 data")
        assert result["payer_tin"] is None
        assert result["rents_box_1"] is None

    def test_recipient_name(self):
        result = extract_1099misc_from_text(SAMPLE_1099MISC)
        assert result["recipient_name"] == "John Doe"


# ---------------------------------------------------------------------------
# Schedule B
# ---------------------------------------------------------------------------

SAMPLE_SCHEDULE_B = """
Schedule B — Interest and Ordinary Dividends

Part I   Interest
Acme Bank                            1,234.56
First National                       2,500.00
City Credit Union                      750.00

4 Add the amounts on line 1            4,484.56

Part II  Ordinary Dividends
Vanguard Total Stock                 3,100.00
Fidelity Growth Fund                   500.00

6 Add the amounts on line 5            3,600.00

Part III Foreign Accounts and Trusts
7a At any time during the year, did you have a financial interest in
or signature authority over a financial account in a foreign country? Yes
8 Country: Switzerland
"""


class TestScheduleB:
    def test_interest_payers(self):
        result = extract_schedule_b_1040_from_text(SAMPLE_SCHEDULE_B)
        payers = result["interest_payers"]
        assert len(payers) >= 2
        names = [p["payer"] for p in payers]
        assert any("Acme" in n for n in names)

    def test_interest_total(self):
        result = extract_schedule_b_1040_from_text(SAMPLE_SCHEDULE_B)
        assert result["interest_total_line_4"] == 4484.56

    def test_dividend_payers(self):
        result = extract_schedule_b_1040_from_text(SAMPLE_SCHEDULE_B)
        payers = result["dividend_payers"]
        assert len(payers) >= 1

    def test_dividend_total(self):
        result = extract_schedule_b_1040_from_text(SAMPLE_SCHEDULE_B)
        assert result["dividend_total_line_6"] == 3600.00

    def test_foreign_accounts_yes(self):
        result = extract_schedule_b_1040_from_text(SAMPLE_SCHEDULE_B)
        assert result["foreign_accounts"] is True

    def test_foreign_country(self):
        result = extract_schedule_b_1040_from_text(SAMPLE_SCHEDULE_B)
        assert result["foreign_country"] is not None
        assert "Switzerland" in result["foreign_country"]

    def test_empty_text(self):
        result = extract_schedule_b_1040_from_text("")
        assert result["interest_payers"] == []
        assert result["interest_total_line_4"] is None


# ---------------------------------------------------------------------------
# Schedule C
# ---------------------------------------------------------------------------

SAMPLE_SCHEDULE_C = """
Schedule C  Profit or Loss From Business
A Principal business  Consulting Services
D EIN: 98-7654321
B business code 541611
F Accounting method Cash

1 Gross receipts or sales 125,000.00
2 Returns and allowances 1,500.00
4 Cost of goods sold 10,000.00
7 Gross income 113,500.00
8 Advertising 2,000.00
9 Car and truck expenses 3,500.00
13 Depreciation section 179 5,000.00
15 Insurance (other than health) 1,200.00
18 Office expense 800.00
22 Supplies 500.00
23 Taxes and licenses 1,000.00
25 Utilities 600.00
28 Total expenses 14,600.00
29 Tentative profit 98,900.00
31 Net profit or loss 98,900.00
"""


class TestScheduleC:
    def test_business_name(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["business_name"] is not None

    def test_ein(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["ein"] == "98-7654321"

    def test_accounting_method(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["accounting_method"] == "Cash"

    def test_gross_receipts(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["gross_receipts_line_1"] == 125000.00

    def test_gross_income(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["gross_income_line_7"] == 113500.00

    def test_total_expenses(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["total_expenses_line_28"] == 14600.00

    def test_net_profit(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["net_profit_loss_line_31"] == 98900.00

    def test_advertising(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["advertising_line_8"] == 2000.00

    def test_depreciation(self):
        result = extract_schedule_c_1040_from_text(SAMPLE_SCHEDULE_C)
        assert result["depreciation_line_13"] == 5000.00

    def test_empty_text(self):
        result = extract_schedule_c_1040_from_text("")
        assert result["gross_receipts_line_1"] is None
        assert result["net_profit_loss_line_31"] is None

