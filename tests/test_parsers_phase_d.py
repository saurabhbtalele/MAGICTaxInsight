"""Unit tests for Phase D parsers: Form 1065, Form 1120-S, Form 1120."""

import pytest

from src.parsers.form1065_parser import extract_1065_from_text
from src.parsers.form1120s_parser import extract_1120s_from_text
from src.parsers.form1120_parser import extract_1120_from_text


# ---------------------------------------------------------------------------
# Form 1065
# ---------------------------------------------------------------------------

SAMPLE_1065 = """
Form 1065  U.S. Return of Partnership Income

Name of partnership  Acme Partners LLC
EIN: 55-1234567
Date business started: 01/01/2020
Accounting method Cash
number of Schedules K-1: 3

1a Gross receipts or sales  500,000.00
1b Returns and allowances  5,000.00
2 Cost of goods sold  200,000.00
3 Gross profit  295,000.00
7 Other income  8,000.00
8 Total income  303,000.00

9 Salaries and wages  80,000.00
10 Guaranteed payments to partners  60,000.00
13 Rent  24,000.00
14 Taxes and licenses  5,000.00
15 Interest  3,000.00
16a Depreciation  12,000.00
20 Other deductions  6,000.00
21 Total deductions  190,000.00
22 Ordinary business income or loss  113,000.00
"""


class TestForm1065:
    def test_ein(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["ein"] == "55-1234567"

    def test_accounting_method(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["accounting_method"] == "Cash"

    def test_number_of_partners(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["number_of_partners"] == "3"

    def test_gross_receipts(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["gross_receipts_line_1a"] == 500000.00

    def test_total_income(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["total_income_line_8"] == 303000.00

    def test_guaranteed_payments(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["guaranteed_payments_line_10"] == 60000.00

    def test_total_deductions(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["total_deductions_line_21"] == 190000.00

    def test_ordinary_income(self):
        result = extract_1065_from_text(SAMPLE_1065)
        assert result["ordinary_business_income_loss_line_22"] == 113000.00

    def test_empty_text(self):
        result = extract_1065_from_text("")
        assert result["ein"] is None
        assert result["gross_receipts_line_1a"] is None


# ---------------------------------------------------------------------------
# Form 1120-S
# ---------------------------------------------------------------------------

SAMPLE_1120S = """
Form 1120-S  U.S. Income Tax Return for an S Corporation

Name  Widgets S-Corp Inc
EIN: 44-9876543
Date incorporated: 06/15/2018
number of shareholders: 2

1a Gross receipts or sales  750,000.00
2 Cost of goods sold  300,000.00
3 Gross profit  450,000.00
5 Other income  5,000.00
6 Total income  455,000.00

7 Compensation of officers  120,000.00
8 Salaries and wages  95,000.00
11 Rents  36,000.00
12 Taxes and licenses  8,000.00
13 Interest  4,500.00
14 Depreciation  18,000.00
19 Other deductions  10,000.00
20 Total deductions  291,500.00
21 Ordinary business income or loss  163,500.00
"""


class TestForm1120S:
    def test_ein(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["ein"] == "44-9876543"

    def test_number_of_shareholders(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["number_of_shareholders"] == "2"

    def test_gross_receipts(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["gross_receipts_line_1a"] == 750000.00

    def test_total_income(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["total_income_line_6"] == 455000.00

    def test_compensation_officers(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["compensation_officers_line_7"] == 120000.00

    def test_total_deductions(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["total_deductions_line_20"] == 291500.00

    def test_ordinary_income(self):
        result = extract_1120s_from_text(SAMPLE_1120S)
        assert result["ordinary_business_income_loss_line_21"] == 163500.00

    def test_empty_text(self):
        result = extract_1120s_from_text("")
        assert result["ein"] is None
        assert result["gross_receipts_line_1a"] is None


# ---------------------------------------------------------------------------
# Form 1120
# ---------------------------------------------------------------------------

SAMPLE_1120 = """
Form 1120  U.S. Corporation Income Tax Return

Corporation  Big Corp International Inc
EIN: 33-1112223
Date incorporated: 03/01/2015

1a Gross receipts or sales  2,000,000.00
2 Cost of goods sold  800,000.00
3 Gross profit  1,200,000.00
5 Interest  15,000.00
6 Gross rents  50,000.00
10 Other income  25,000.00
11 Total income  1,290,000.00

12 Compensation of officers  250,000.00
13 Salaries and wages  400,000.00
16 Rents  60,000.00
17 Taxes and licenses  30,000.00
18 Interest  20,000.00
20 Depreciation  45,000.00
22 Advertising  35,000.00
26 Other deductions  50,000.00
27 Total deductions  890,000.00
30 Taxable income  400,000.00
31 Total tax  84,000.00
"""


class TestForm1120:
    def test_ein(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["ein"] == "33-1112223"

    def test_gross_receipts(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["gross_receipts_line_1a"] == 2000000.00

    def test_total_income(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["total_income_line_11"] == 1290000.00

    def test_total_deductions(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["total_deductions_line_27"] == 890000.00

    def test_taxable_income(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["taxable_income_line_30"] == 400000.00

    def test_total_tax(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["total_tax_line_31"] == 84000.00

    def test_compensation_officers(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["compensation_officers_line_12"] == 250000.00

    def test_advertising(self):
        result = extract_1120_from_text(SAMPLE_1120)
        assert result["advertising_line_22"] == 35000.00

    def test_empty_text(self):
        result = extract_1120_from_text("")
        assert result["ein"] is None
        assert result["taxable_income_line_30"] is None
