"""Unit tests for Phase C parsers: Schedule D, Schedule E, Schedule F."""

import pytest

from src.parsers.schedule_d_1040_parser import extract_schedule_d_1040_from_text
from src.parsers.schedule_e_1040_parser import extract_schedule_e_1040_from_text
from src.parsers.schedule_f_1040_parser import extract_schedule_f_1040_from_text


# ---------------------------------------------------------------------------
# Schedule D
# ---------------------------------------------------------------------------

SAMPLE_SCHEDULE_D = """
Schedule D  Capital Gains and Losses

Part I  Short-Term Capital Gains and Losses

1a 100 sh XYZ Corp  01/15/2023  06/20/2023  15,000  10,000  5,000

7 Net short-term capital gain  5,000.00

Part II  Long-Term Capital Gains and Losses

8a 200 sh ABC Inc   03/10/2020  09/15/2023  40,000  25,000  15,000

15 Net long-term capital gain  15,000.00

Part III  Summary
16 Combine lines 7 and 15  20,000.00
21 Net capital gain or loss  20,000.00
"""


class TestScheduleD:
    def test_net_short_term(self):
        result = extract_schedule_d_1040_from_text(SAMPLE_SCHEDULE_D)
        assert result["net_short_term_gain_loss_line_7"] == 5000.00

    def test_net_long_term(self):
        result = extract_schedule_d_1040_from_text(SAMPLE_SCHEDULE_D)
        assert result["net_long_term_gain_loss_line_15"] == 15000.00

    def test_combined_line_16(self):
        result = extract_schedule_d_1040_from_text(SAMPLE_SCHEDULE_D)
        assert result["combined_line_16"] == 20000.00

    def test_short_term_transactions_list(self):
        result = extract_schedule_d_1040_from_text(SAMPLE_SCHEDULE_D)
        assert isinstance(result["short_term_transactions"], list)

    def test_long_term_transactions_list(self):
        result = extract_schedule_d_1040_from_text(SAMPLE_SCHEDULE_D)
        assert isinstance(result["long_term_transactions"], list)

    def test_empty_text(self):
        result = extract_schedule_d_1040_from_text("")
        assert result["net_short_term_gain_loss_line_7"] is None
        assert result["net_long_term_gain_loss_line_15"] is None
        assert result["short_term_transactions"] == []
        assert result["long_term_transactions"] == []


# ---------------------------------------------------------------------------
# Schedule E
# ---------------------------------------------------------------------------

SAMPLE_SCHEDULE_E = """
Schedule E  Supplemental Income and Loss

Part I  Income or Loss From Rental Real Estate and Royalties

3 Rents received  24,000.00
4 Royalties received  0.00

9 Insurance  1,200.00
12 Mortgage interest paid  8,400.00
14 Repairs  2,300.00
16 Taxes  3,000.00
17 Utilities  1,800.00
18 Depreciation  5,000.00

20 Total expenses  21,700.00
21 Income or loss  2,300.00

26 Total rental real estate and royalty income  2,300.00
"""


class TestScheduleE:
    def test_rents_received(self):
        result = extract_schedule_e_1040_from_text(SAMPLE_SCHEDULE_E)
        assert result["rents_received_line_3"] == 24000.00

    def test_total_expenses(self):
        result = extract_schedule_e_1040_from_text(SAMPLE_SCHEDULE_E)
        assert result["total_expenses_line_20"] == 21700.00

    def test_income_or_loss(self):
        result = extract_schedule_e_1040_from_text(SAMPLE_SCHEDULE_E)
        assert result["income_or_loss_line_21"] == 2300.00

    def test_total_rental(self):
        result = extract_schedule_e_1040_from_text(SAMPLE_SCHEDULE_E)
        assert result["total_rental_real_estate_line_26"] == 2300.00

    def test_expenses_dict(self):
        result = extract_schedule_e_1040_from_text(SAMPLE_SCHEDULE_E)
        assert isinstance(result["expenses"], dict)

    def test_properties_list(self):
        result = extract_schedule_e_1040_from_text(SAMPLE_SCHEDULE_E)
        assert isinstance(result["properties"], list)

    def test_empty_text(self):
        result = extract_schedule_e_1040_from_text("")
        assert result["rents_received_line_3"] is None
        assert result["properties"] == []


# ---------------------------------------------------------------------------
# Schedule F
# ---------------------------------------------------------------------------

SAMPLE_SCHEDULE_F = """
Schedule F  Profit or Loss From Farming
D EIN: 11-2233445
F Accounting method Cash
B Principal crop or activity Corn

9 Gross farm income  180,000.00

12 Car and truck expenses  4,500.00
13 Chemicals  8,000.00
18 Feed  22,000.00
19 Fertilizers and lime  12,000.00
22 Insurance  3,500.00
24 Labor hired  15,000.00
27 Repairs and maintenance  6,000.00
30 Supplies  3,000.00
31 Taxes  4,000.00
32 Utilities  2,500.00

35 Total expenses  80,500.00
36 Net farm profit or loss  99,500.00
"""


class TestScheduleF:
    def test_ein(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["ein"] == "11-2233445"

    def test_accounting_method(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["accounting_method"] == "Cash"

    def test_gross_income(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["gross_income_line_9"] == 180000.00

    def test_total_expenses(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["total_expenses_line_35"] == 80500.00

    def test_net_farm_profit(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["net_farm_profit_loss_line_36"] == 99500.00

    def test_chemicals(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["chemicals_line_13"] == 8000.00

    def test_feed(self):
        result = extract_schedule_f_1040_from_text(SAMPLE_SCHEDULE_F)
        assert result["feed_line_18"] == 22000.00

    def test_empty_text(self):
        result = extract_schedule_f_1040_from_text("")
        assert result["gross_income_line_9"] is None
        assert result["net_farm_profit_loss_line_36"] is None

