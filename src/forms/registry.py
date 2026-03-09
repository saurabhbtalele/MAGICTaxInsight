from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ExtractionTier(Enum):
    """Ordered tiers for form field extraction — tried top-to-bottom."""

    PDFPLUMBER = "pdfplumber"
    DOCLING = "docling"
    AZURE_PREBUILT = "azure_prebuilt"
    AZURE_CUSTOM = "azure_custom"
    LLM_FALLBACK = "llm_fallback"


@dataclass
class FormFieldDefinition:
    name: str
    label_patterns: List[str]
    value_type: str = "str"  # "str", "int", "float", "currency", "ssn", "date"
    optional: bool = False


@dataclass
class FormSchema:
    form_id: str
    display_name: str
    detection_patterns: List[str]
    fields: List[FormFieldDefinition] = field(default_factory=list)
    azure_model_id: str | None = None
    extraction_tier: ExtractionTier = ExtractionTier.PDFPLUMBER


FORM_REGISTRY: Dict[str, FormSchema] = {
    # ------------------------------------------------------------------
    # W-2  (all 10 fields; dedicated pdfplumber parser fills these)
    # ------------------------------------------------------------------
    "W-2": FormSchema(
        form_id="W-2",
        display_name="Form W-2 (Wage and Tax Statement)",
        detection_patterns=[
            "Form W-2",
            "Wage and Tax Statement",
            "Employee's SSA number",
            "Employer's FED ID number",
            "Wages, tips, other comp.",
        ],
        fields=[
            FormFieldDefinition("employee_ssn",
                ["Employee's SSA number", "Employee's social security number"],
                value_type="ssn"),
            FormFieldDefinition("employer_ein",
                ["Employer's FED ID number", "Employer identification number", "EIN"],
                value_type="ssn"),
            FormFieldDefinition("employee_name",
                ["Employee's name"], value_type="str", optional=True),
            FormFieldDefinition("employer_name",
                ["Employer's name"], value_type="str", optional=True),
            FormFieldDefinition("wages_tips_other_compensation_box_1",
                ["Wages, tips, other comp.", "1 Wages, tips, other compensation"],
                value_type="currency"),
            FormFieldDefinition("federal_income_tax_withheld_box_2",
                ["Federal income tax withheld", "2 Federal income tax withheld"],
                value_type="currency"),
            FormFieldDefinition("social_security_wages_box_3",
                ["Social security wages", "3 Social security wages"],
                value_type="currency", optional=True),
            FormFieldDefinition("social_security_tax_withheld_box_4",
                ["Social security tax withheld", "4 Social security tax withheld"],
                value_type="currency", optional=True),
            FormFieldDefinition("medicare_wages_tips_box_5",
                ["Medicare wages and tips", "5 Medicare wages"],
                value_type="currency", optional=True),
            FormFieldDefinition("medicare_tax_withheld_box_6",
                ["Medicare tax withheld", "6 Medicare tax withheld"],
                value_type="currency", optional=True),
        ],
        azure_model_id="tax.us.w2",
        extraction_tier=ExtractionTier.DOCLING,
    ),

    # ------------------------------------------------------------------
    # 1099-NEC  (dedicated pdfplumber parser fills these)
    # ------------------------------------------------------------------
    "1099-NEC": FormSchema(
        form_id="1099-NEC",
        display_name="Form 1099-NEC (Nonemployee Compensation)",
        detection_patterns=[
            "Form 1099-NEC",
            "1099-NEC",
            "Nonemployee compensation",
            "Nonemployee Compensation",
        ],
        fields=[
            FormFieldDefinition("payer_name",
                ["Payer's name"], value_type="str", optional=True),
            FormFieldDefinition("payer_tin",
                ["PAYER'S TIN", "Payer's TIN"], value_type="ssn"),
            FormFieldDefinition("recipient_tin",
                ["RECIPIENT'S TIN", "Recipient's TIN"], value_type="ssn"),
            FormFieldDefinition("recipient_name",
                ["RECIPIENT'S name", "Recipient's name"], value_type="str", optional=True),
            FormFieldDefinition("nonemployee_compensation_box_1",
                ["1 Nonemployee compensation", "Nonemployee compensation"],
                value_type="currency"),
            FormFieldDefinition("federal_income_tax_withheld_box_4",
                ["4 Federal income tax withheld", "Federal income tax withheld"],
                value_type="currency", optional=True),
        ],
        azure_model_id="tax.us.1099NEC.2023",
        extraction_tier=ExtractionTier.DOCLING,
    ),

    # ------------------------------------------------------------------
    # 1099-R  (dedicated pdfplumber parser fills these)
    # ------------------------------------------------------------------
    "1099-R": FormSchema(
        form_id="1099-R",
        display_name="Form 1099-R (Distributions From Pensions, IRAs, etc.)",
        detection_patterns=[
            "Form 1099-R",
            "1099-R",
            "Distributions From Pensions",
            "Gross distribution",
        ],
        fields=[
            FormFieldDefinition("payer_name",
                ["Payer's name"], value_type="str", optional=True),
            FormFieldDefinition("payer_tin",
                ["PAYER'S TIN", "Payer's TIN"], value_type="ssn"),
            FormFieldDefinition("recipient_tin",
                ["RECIPIENT'S TIN", "Recipient's TIN"], value_type="ssn"),
            FormFieldDefinition("gross_distribution_box_1",
                ["1 Gross distribution", "Gross distribution"],
                value_type="currency"),
            FormFieldDefinition("taxable_amount_box_2a",
                ["2a Taxable amount", "Taxable amount"],
                value_type="currency", optional=True),
            FormFieldDefinition("federal_income_tax_withheld_box_4",
                ["4 Federal income tax withheld", "Federal income tax withheld"],
                value_type="currency", optional=True),
            FormFieldDefinition("distribution_code_box_7",
                ["7 Distribution code", "Distribution code"],
                value_type="str", optional=True),
        ],
        azure_model_id="tax.us.1099R.2023",
        extraction_tier=ExtractionTier.DOCLING,
    ),

    # ------------------------------------------------------------------
    # Form 1040  (dedicated pdfplumber parser fills these)
    # ------------------------------------------------------------------
    "1040": FormSchema(
        form_id="1040",
        display_name="Form 1040 (U.S. Individual Income Tax Return)",
        detection_patterns=[
            "Form 1040",
            "U.S. Individual Income Tax Return",
        ],
        fields=[
            FormFieldDefinition("wages_salaries_tips_line_1",
                ["1a Wages, salaries, tips", "1 Wages, salaries, tips"],
                value_type="currency"),
            FormFieldDefinition("adjusted_gross_income_line_11",
                ["11 Adjusted gross income"], value_type="currency"),
            FormFieldDefinition("taxable_income_line_15",
                ["15 Taxable income"], value_type="currency"),
            FormFieldDefinition("total_tax_line_24",
                ["24 Total tax"], value_type="currency"),
            FormFieldDefinition("federal_tax_withheld_line_25",
                ["25a Federal income tax withheld", "25 Federal income tax withheld"],
                value_type="currency", optional=True),
            FormFieldDefinition("amount_refunded_line_34",
                ["34 Amount of line", "34 Refund"],
                value_type="currency", optional=True),
            FormFieldDefinition("amount_owed_line_37",
                ["37 Amount you owe", "37 Amount owe"],
                value_type="currency", optional=True),
        ],
        azure_model_id="tax.us.1040.2023",
        extraction_tier=ExtractionTier.DOCLING,
    ),

    # ------------------------------------------------------------------
    # Schedule C
    # ------------------------------------------------------------------
    "Schedule C (1040)": FormSchema(
        form_id="Schedule C (1040)",
        display_name="Schedule C (Form 1040) — Profit or Loss From Business",
        detection_patterns=[
            "Schedule C (1040)",
            "Profit or Loss From Business",
        ],
        fields=[
            FormFieldDefinition("business_name",
                ["A Principal business"], value_type="str", optional=True),
            FormFieldDefinition("gross_receipts_line_1",
                ["1 Gross receipts", "Gross receipts"], value_type="currency"),
            FormFieldDefinition("gross_income_line_7",
                ["7 Gross income"], value_type="currency", optional=True),
            FormFieldDefinition("total_expenses_line_28",
                ["28 Total expenses"], value_type="currency", optional=True),
            FormFieldDefinition("net_profit_or_loss_line_31",
                ["31 Net profit or", "31 Net profit"],
                value_type="currency"),
        ],
        azure_model_id="tax.us.1040ScheduleC.2023",
        extraction_tier=ExtractionTier.DOCLING,
    ),
    # ------------------------------------------------------------------
    # Schedule K (Form 1065) — Partnership Aggregate Distributive Share
    # This is Form 1065 Page 4 (Schedule K), NOT the individual K-1 slip.
    # Same box structure as K-1; reuses the k1_1065 coordinate-based parser.
    # ------------------------------------------------------------------
    "Schedule K (1065)": FormSchema(
        form_id="Schedule K (1065)",
        display_name="Schedule K (Form 1065) — Partners' Distributive Share Items",
        detection_patterns=[
            "Distributive Share Items Total amount",
            "Schedule K Partners",
        ],
        fields=[],
        extraction_tier=ExtractionTier.PDFPLUMBER,
    ),

    # ------------------------------------------------------------------
    # K-1 (Form 1065) — Partner's Share of Income
    # No Azure DI prebuilt model exists; dedicated pdfplumber parser used.
    # ------------------------------------------------------------------
    "K-1 (1065)": FormSchema(
        form_id="K-1 (1065)",
        display_name="Schedule K-1 (Form 1065) — Partner's Share of Income",
        detection_patterns=[
            "Schedule K-1 (Form 1065)",
            "K-1 (Form 1065)",
            "Partner's Share of Income",
        ],
        fields=[
            FormFieldDefinition("partnership_ein",
                ["Partnership's employer identification number", "Partnership EIN"],
                value_type="str", optional=True),
            FormFieldDefinition("partnership_name",
                ["Partnership's name", "Name of partnership"],
                value_type="str", optional=True),
            FormFieldDefinition("partner_tin",
                ["Partner's SSN or TIN", "Partner's identifying number"],
                value_type="str", optional=True),
            FormFieldDefinition("partner_name",
                ["Partner's name"], value_type="str", optional=True),
            FormFieldDefinition("ownership_percentage",
                ["J Profit", "Profit Loss Capital"],
                value_type="float", optional=True),
            FormFieldDefinition("ordinary_business_income_loss_box_1",
                ["1 Ordinary business income (loss)", "Ordinary business income"],
                value_type="currency"),
            FormFieldDefinition("net_rental_real_estate_income_loss_box_2",
                ["2 Net rental real estate income (loss)"],
                value_type="currency", optional=True),
            FormFieldDefinition("other_net_rental_income_loss_box_3",
                ["3 Other net rental income (loss)"],
                value_type="currency", optional=True),
            FormFieldDefinition("guaranteed_payments_services_box_4a",
                ["4a Guaranteed payments for services"],
                value_type="currency", optional=True),
            FormFieldDefinition("guaranteed_payments_capital_box_4b",
                ["4b Guaranteed payments for capital"],
                value_type="currency", optional=True),
            FormFieldDefinition("guaranteed_payments_total_box_4c",
                ["4c Total guaranteed payments", "4 Guaranteed payments"],
                value_type="currency", optional=True),
            FormFieldDefinition("interest_income_box_5",
                ["5 Interest income"], value_type="currency", optional=True),
            FormFieldDefinition("ordinary_dividends_box_6a",
                ["6a Ordinary dividends", "6 Ordinary dividends"],
                value_type="currency", optional=True),
            FormFieldDefinition("qualified_dividends_box_6b",
                ["6b Qualified dividends"], value_type="currency", optional=True),
            FormFieldDefinition("royalties_box_7",
                ["7 Royalties"], value_type="currency", optional=True),
            FormFieldDefinition("net_short_term_capital_gain_loss_box_8",
                ["8 Net short-term capital gain (loss)"],
                value_type="currency", optional=True),
            FormFieldDefinition("net_long_term_capital_gain_loss_box_9a",
                ["9a Net long-term capital gain (loss)", "9 Net long-term capital gain"],
                value_type="currency", optional=True),
            FormFieldDefinition("net_section_1231_gain_loss_box_10",
                ["10 Net section 1231 gain (loss)"],
                value_type="currency", optional=True),
            FormFieldDefinition("section_179_deduction_box_12",
                ["12 Section 179 deduction"], value_type="currency", optional=True),
            FormFieldDefinition("self_employment_earnings_loss_box_14",
                ["14 Self-employment earnings (loss)", "14 Self-employment"],
                value_type="currency", optional=True),
            FormFieldDefinition("distributions_box_19",
                ["19 Distributions", "19a Cash and marketable securities"],
                value_type="currency", optional=True),
        ],
        extraction_tier=ExtractionTier.PDFPLUMBER,
    ),

    # ------------------------------------------------------------------
    # K-1 (Form 1120-S) — Shareholder's Share of Income
    # ------------------------------------------------------------------
    "K-1 (1120-S)": FormSchema(
        form_id="K-1 (1120-S)",
        display_name="Schedule K-1 (Form 1120-S) — Shareholder's Share of Income",
        detection_patterns=[
            "Schedule K-1 (Form 1120-S)",
            "K-1 (Form 1120-S)",
            "Shareholder's Share of Income",
        ],
        fields=[
            FormFieldDefinition("s_corp_ein", ["Corporation's employer identification number", "Corporation EIN"], value_type="str", optional=True),
            FormFieldDefinition("s_corp_name", ["Corporation's name", "Name of corporation"], value_type="str", optional=True),
            FormFieldDefinition("shareholder_tin", ["Shareholder's identifying number", "Shareholder's SSN or TIN"], value_type="str", optional=True),
            FormFieldDefinition("shareholder_name", ["Shareholder's name", "Name of shareholder"], value_type="str", optional=True),
            FormFieldDefinition("ownership_percentage", ["Shareholder's percentage of stock ownership", "Ownership percentage"], value_type="str", optional=True),
            FormFieldDefinition("ordinary_business_income_loss_box_1", ["1 Ordinary business income"], value_type="currency", optional=True),
            FormFieldDefinition("net_rental_real_estate_income_loss_box_2", ["2 Net rental real estate income"], value_type="currency", optional=True),
            FormFieldDefinition("other_net_rental_income_loss_box_3", ["3 Other net rental income"], value_type="currency", optional=True),
            FormFieldDefinition("interest_income_box_4", ["4 Interest income"], value_type="currency", optional=True),
            FormFieldDefinition("ordinary_dividends_box_5a", ["5a Ordinary dividends"], value_type="currency", optional=True),
            FormFieldDefinition("qualified_dividends_box_5b", ["5b Qualified dividends"], value_type="currency", optional=True),
            FormFieldDefinition("royalties_box_6", ["6 Royalties"], value_type="currency", optional=True),
            FormFieldDefinition("net_short_term_capital_gain_loss_box_7", ["7 Net short-term capital gain"], value_type="currency", optional=True),
            FormFieldDefinition("net_long_term_capital_gain_loss_box_8a", ["8a Net long-term capital gain"], value_type="currency", optional=True),
            FormFieldDefinition("collectibles_gain_loss_box_8b", ["8b Collectibles"], value_type="currency", optional=True),
            FormFieldDefinition("unrecaptured_sec1250_gain_box_8c", ["8c Unrecaptured section 1250"], value_type="currency", optional=True),
            FormFieldDefinition("net_section_1231_gain_loss_box_9", ["9 Net section 1231 gain"], value_type="currency", optional=True),
            FormFieldDefinition("other_income_loss_box_10", ["10 Other income"], value_type="currency", optional=True),
            FormFieldDefinition("section_179_deduction_box_11", ["11 Section 179 deduction"], value_type="currency", optional=True),
            FormFieldDefinition("other_deductions_box_12", ["12 Other deductions"], value_type="currency", optional=True),
            FormFieldDefinition("credits_box_13", ["13 Credits"], value_type="currency", optional=True),
            FormFieldDefinition("distributions_box_16", ["16 Items affecting shareholder basis", "16D Distributions"], value_type="currency", optional=True),
            FormFieldDefinition("other_information_box_17", ["17 Other information"], value_type="currency", optional=True),
        ],
        extraction_tier=ExtractionTier.PDFPLUMBER,
    ),

    # ------------------------------------------------------------------
    # 1099-MISC
    # ------------------------------------------------------------------
    "1099-MISC": FormSchema(
        form_id="1099-MISC",
        display_name="Form 1099-MISC (Miscellaneous Information)",
        detection_patterns=[
            "Form 1099-MISC",
            "Miscellaneous Income",
            "Miscellaneous Information",
        ],
        fields=[
            FormFieldDefinition("payer_name", ["Payer's name"], optional=True),
            FormFieldDefinition("payer_tin", ["PAYER'S TIN"], value_type="ssn"),
            FormFieldDefinition("recipient_tin", ["RECIPIENT'S TIN"], value_type="ssn"),
            FormFieldDefinition("recipient_name", ["RECIPIENT'S name"], optional=True),
            FormFieldDefinition("rents_box_1", ["1 Rents"], value_type="currency", optional=True),
            FormFieldDefinition("royalties_box_2", ["2 Royalties"], value_type="currency", optional=True),
            FormFieldDefinition("other_income_box_3", ["3 Other income"], value_type="currency", optional=True),
            FormFieldDefinition("federal_income_tax_withheld_box_4", ["4 Federal income tax withheld"], value_type="currency", optional=True),
            FormFieldDefinition("fishing_boat_proceeds_box_5", ["5 Fishing boat proceeds"], value_type="currency", optional=True),
            FormFieldDefinition("medical_payments_box_6", ["6 Medical and health care payments"], value_type="currency", optional=True),
            FormFieldDefinition("nonemployee_compensation_box_7", ["7 Nonemployee compensation"], value_type="currency", optional=True),
            FormFieldDefinition("substitute_payments_box_8", ["8 Substitute payments"], value_type="currency", optional=True),
            FormFieldDefinition("crop_insurance_box_10", ["10 Crop insurance proceeds"], value_type="currency", optional=True),
            FormFieldDefinition("excess_golden_parachute_box_13", ["13 Excess golden parachute"], value_type="currency", optional=True),
            FormFieldDefinition("gross_proceeds_attorney_box_14", ["14 Gross proceeds to an attorney"], value_type="currency", optional=True),
        ],
    ),

    # ------------------------------------------------------------------
    # Schedule B
    # ------------------------------------------------------------------
    "Schedule B (1040)": FormSchema(
        form_id="Schedule B (1040)",
        display_name="Schedule B (Form 1040) — Interest and Ordinary Dividends",
        detection_patterns=[
            "Schedule B (1040)",
            "Interest and Ordinary Dividends",
        ],
        fields=[
            FormFieldDefinition("interest_total_line_4", ["Add the amounts on line 1", "4 Add"], value_type="currency"),
            FormFieldDefinition("dividend_total_line_6", ["Add the amounts on line 5", "6 Add"], value_type="currency"),
            FormFieldDefinition("foreign_accounts", ["7a", "foreign bank", "securities account"], value_type="str", optional=True),
        ],
    ),

    # ------------------------------------------------------------------
    # Schedule D
    # ------------------------------------------------------------------
    "Schedule D (1040)": FormSchema(
        form_id="Schedule D (1040)",
        display_name="Schedule D (Form 1040) — Capital Gains and Losses",
        detection_patterns=[
            "Schedule D (1040)",
            "Capital Gains and Losses",
        ],
        fields=[
            FormFieldDefinition("net_short_term_gain_loss_line_7",
                ["7 Net short-term", "7 Total short-term"],
                value_type="currency"),
            FormFieldDefinition("net_long_term_gain_loss_line_15",
                ["15 Net long-term", "15 Total long-term"],
                value_type="currency"),
            FormFieldDefinition("combined_line_16",
                ["16 Combine"], value_type="currency", optional=True),
            FormFieldDefinition("combined_line_21",
                ["21 Combine", "21 Net"], value_type="currency", optional=True),
        ],
    ),

    # ------------------------------------------------------------------
    # Schedule E
    # ------------------------------------------------------------------
    "Schedule E (1040)": FormSchema(
        form_id="Schedule E (1040)",
        display_name="Schedule E (Form 1040) — Supplemental Income and Loss",
        detection_patterns=[
            "Schedule E (1040)",
            "Supplemental Income and Loss",
        ],
        fields=[
            FormFieldDefinition("rents_received_line_3",
                ["3 Rents received", "Rents received"],
                value_type="currency", optional=True),
            FormFieldDefinition("total_expenses_line_20",
                ["20 Total expenses"], value_type="currency", optional=True),
            FormFieldDefinition("income_or_loss_line_21",
                ["21 Income", "21 loss"], value_type="currency", optional=True),
            FormFieldDefinition("total_rental_real_estate_line_26",
                ["26 Total rental real estate"],
                value_type="currency", optional=True),
        ],
    ),

    # ------------------------------------------------------------------
    # Schedule F
    # ------------------------------------------------------------------
    "Schedule F (1040)": FormSchema(
        form_id="Schedule F (1040)",
        display_name="Schedule F (Form 1040) — Profit or Loss From Farming",
        detection_patterns=[
            "Schedule F (1040)",
            "Profit or Loss From Farming",
        ],
        fields=[
            FormFieldDefinition("gross_income_line_9",
                ["9 Gross income", "9 Gross farm income"],
                value_type="currency"),
            FormFieldDefinition("total_expenses_line_35",
                ["35 Total expenses"], value_type="currency", optional=True),
            FormFieldDefinition("net_farm_profit_loss_line_36",
                ["36 Net farm profit", "36 Net farm loss"],
                value_type="currency"),
        ],
    ),

    # ------------------------------------------------------------------
    # Form 1065  (Partnership Return)
    # ------------------------------------------------------------------
    "1065": FormSchema(
        form_id="1065",
        display_name="Form 1065 (U.S. Return of Partnership Income)",
        detection_patterns=[
            "Form 1065",
            "U.S. Return of Partnership Income",
        ],
        fields=[
            FormFieldDefinition("ein",
                ["EIN", "Employer identification number"],
                value_type="ssn"),
            FormFieldDefinition("gross_receipts_line_1a",
                ["1a Gross receipts", "Gross receipts or sales"],
                value_type="currency"),
            FormFieldDefinition("total_income_line_8",
                ["8 Total income"], value_type="currency"),
            FormFieldDefinition("total_deductions_line_21",
                ["21 Total deductions"], value_type="currency", optional=True),
            FormFieldDefinition("ordinary_business_income_loss_line_22",
                ["22 Ordinary business income"],
                value_type="currency"),
        ],
    ),

    # ------------------------------------------------------------------
    # Form 1120-S  (S-Corp Return)
    # ------------------------------------------------------------------
    "1120-S": FormSchema(
        form_id="1120-S",
        display_name="Form 1120-S (U.S. Income Tax Return for an S Corporation)",
        detection_patterns=[
            "Form 1120-S",
            "U.S. Income Tax Return for an S Corporation",
        ],
        fields=[
            # Identity (Box A-I)
            FormFieldDefinition("ein", ["EIN", "Employer identification number"], value_type="ssn"),
            FormFieldDefinition("corporation_name", ["Name"], value_type="str"),
            FormFieldDefinition("address", ["Number and street"], value_type="str", optional=True),
            FormFieldDefinition("city", ["City or town"], value_type="str", optional=True),
            FormFieldDefinition("state", ["State or province"], value_type="str", optional=True),
            FormFieldDefinition("zip", ["ZIP or foreign postal code"], value_type="str", optional=True),
            FormFieldDefinition("s_election_date", ["A S election effective date"], value_type="date", optional=True),
            FormFieldDefinition("business_activity_code", ["B Business activity code"], value_type="str", optional=True),
            FormFieldDefinition("date_incorporated", ["E Date incorporated"], value_type="date", optional=True),
            FormFieldDefinition("total_assets", ["F Total assets"], value_type="currency", optional=True),
            FormFieldDefinition("number_of_shareholders", ["I Enter the number of shareholders"], value_type="int", optional=True),
            
            # Page 1 Income
            FormFieldDefinition("gross_receipts_line_1a", ["1a Gross receipts or sales"], value_type="currency"),
            FormFieldDefinition("returns_allowances_line_1b", ["1b Less returns and allowances"], value_type="currency", optional=True),
            FormFieldDefinition("cost_of_goods_sold_line_2", ["2 Cost of goods sold"], value_type="currency", optional=True),
            FormFieldDefinition("gross_profit_line_3", ["3 Gross profit"], value_type="currency", optional=True),
            FormFieldDefinition("net_gain_loss_line_4", ["4 Net gain (loss)"], value_type="currency", optional=True),
            FormFieldDefinition("other_income_line_5", ["5 Other income (loss)"], value_type="currency", optional=True),
            FormFieldDefinition("total_income_line_6", ["6 Total income (loss)"], value_type="currency"),
            
            # Page 1 Deductions
            FormFieldDefinition("compensation_officers_line_7", ["7 Compensation of officers"], value_type="currency", optional=True),
            FormFieldDefinition("salaries_wages_line_8", ["8 Salaries and wages"], value_type="currency", optional=True),
            FormFieldDefinition("repairs_maintenance_line_9", ["9 Repairs and maintenance"], value_type="currency", optional=True),
            FormFieldDefinition("bad_debts_line_10", ["10 Bad debts"], value_type="currency", optional=True),
            FormFieldDefinition("rents_line_11", ["11 Rents"], value_type="currency", optional=True),
            FormFieldDefinition("taxes_licenses_line_12", ["12 Taxes and licenses"], value_type="currency", optional=True),
            FormFieldDefinition("interest_line_13", ["13 Interest"], value_type="currency", optional=True),
            FormFieldDefinition("depreciation_line_14", ["14 Depreciation"], value_type="currency", optional=True),
            FormFieldDefinition("depletion_line_15", ["15 Depletion"], value_type="currency", optional=True),
            FormFieldDefinition("advertising_line_16", ["16 Advertising"], value_type="currency", optional=True),
            FormFieldDefinition("pension_plans_line_17", ["17 Pension, profit-sharing"], value_type="currency", optional=True),
            FormFieldDefinition("employee_benefit_line_18", ["18 Employee benefit"], value_type="currency", optional=True),
            FormFieldDefinition("energy_deduction_line_19", ["19 Energy efficient"], value_type="currency", optional=True),
            FormFieldDefinition("other_deductions_line_20", ["20 Other deductions"], value_type="currency", optional=True),
            FormFieldDefinition("total_deductions_line_21", ["21 Total deductions"], value_type="currency"),
            
            # Page 1 Totals & Tax
            FormFieldDefinition("ordinary_business_income_loss_line_22", ["22 Ordinary business income"], value_type="currency"),
            FormFieldDefinition("excess_passive_tax_line_23a", ["23a Excess net passive income"], value_type="currency", optional=True),
            FormFieldDefinition("schedule_d_tax_line_23b", ["23b Tax from Schedule D"], value_type="currency", optional=True),
            FormFieldDefinition("total_tax_line_23c", ["23c Add lines 23a and 23b"], value_type="currency", optional=True),
            FormFieldDefinition("estimated_tax_payments_line_24a", ["24a Current year’s estimated tax"], value_type="currency", optional=True),
            FormFieldDefinition("tax_deposited_7004_line_24b", ["24b Tax deposited with Form 7004"], value_type="currency", optional=True),
            FormFieldDefinition("fuel_tax_credit_line_24c", ["24c Credit for federal tax paid on fuels"], value_type="currency", optional=True),
            FormFieldDefinition("total_payments_line_24z", ["24z Add lines 24a through 24d"], value_type="currency", optional=True),
            FormFieldDefinition("estimated_tax_penalty_line_25", ["25 Estimated tax penalty"], value_type="currency", optional=True),
            FormFieldDefinition("amount_owed_line_26", ["26 Amount owed"], value_type="currency", optional=True),
            FormFieldDefinition("overpayment_line_27", ["27 Overpayment"], value_type="currency", optional=True),
            
            # Schedule K (Page 3)
            FormFieldDefinition("k_ordinary_income_line_1", ["1 Ordinary business income (loss)"], value_type="currency", optional=True),
            FormFieldDefinition("k_rental_income_line_2", ["2 Net rental real estate"], value_type="currency", optional=True),
            FormFieldDefinition("k_interest_income_line_4", ["4 Interest income"], value_type="currency", optional=True),
            FormFieldDefinition("k_ordinary_dividends_line_5a", ["5a Ordinary dividends"], value_type="currency", optional=True),
            FormFieldDefinition("k_qualified_dividends_line_5b", ["5b Qualified dividends"], value_type="currency", optional=True),
            FormFieldDefinition("k_royalties_line_6", ["6 Royalties"], value_type="currency", optional=True),
            FormFieldDefinition("k_net_short_term_gain_line_7", ["7 Net short-term capital gain"], value_type="currency", optional=True),
            FormFieldDefinition("k_net_long_term_gain_line_8a", ["8a Net long-term capital gain"], value_type="currency", optional=True),
            FormFieldDefinition("k_section_179_deduction_line_11", ["11 Section 179 deduction"], value_type="currency", optional=True),
            FormFieldDefinition("k_distributions_line_16d", ["16d Distributions"], value_type="currency", optional=True),

            # Schedule B (Page 2) - Other Information
            FormFieldDefinition("sch_b_q1a_yes", ["1a"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q1a_no", ["1a"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q1b_yes", ["1b"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q1b_no", ["1b"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q2_yes", ["2 Own directly an interest of 20%"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q2_no", ["2 Own directly an interest of 20%"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q3_yes", ["3"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q3_no", ["3"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q4a_yes", ["4a"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q4a_no", ["4a"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q4b_yes", ["4b"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q4b_no", ["4b"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q5a_yes", ["5a"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q5a_no", ["5a"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q5a_i", ["(i) Total shares of restricted stock"], value_type="int", optional=True),
            FormFieldDefinition("sch_b_q5a_ii", ["(ii) Total shares of non-restricted stock"], value_type="int", optional=True),
            FormFieldDefinition("sch_b_q5b_yes", ["5b"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q5b_no", ["5b"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q5b_i", ["(i) Total shares of stock outstanding"], value_type="int", optional=True),
            FormFieldDefinition("sch_b_q5b_ii", ["(ii) Total shares of stock outstanding if"], value_type="int", optional=True),
            FormFieldDefinition("sch_b_q6_yes", ["6 Has this corporation filed, or is it required"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q6_no", ["6 Has this corporation filed, or is it required"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q7_checkbox", ["7 Check this box if the corporation issued"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q8_yes", ["8 If the corporation"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q8_no", ["8 If the corporation"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q8_amount", ["8 If the corporation"], value_type="currency", optional=True),
            FormFieldDefinition("sch_b_q9_yes", ["9 Did the corporation have an election under section 163"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q9_no", ["9 Did the corporation have an election under section 163"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q10_yes", ["10 Does the corporation satisfy one or more"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q10_no", ["10 Does the corporation satisfy one or more"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q11_yes", ["11 Does the corporation satisfy both"], value_type="boolean", optional=True),
            FormFieldDefinition("sch_b_q11_no", ["11 Does the corporation satisfy both"], value_type="boolean", optional=True),

            # Schedule K (Continued - Page 3)
            FormFieldDefinition("k_investment_income_line_17a", ["17a Investment income"], value_type="currency", optional=True),
            FormFieldDefinition("k_investment_expenses_line_17b", ["17b Investment expenses"], value_type="currency", optional=True),
            FormFieldDefinition("k_dividend_distributions_line_17c", ["17c Dividend distributions paid from accumulated earnings"], value_type="currency", optional=True),
            FormFieldDefinition("k_other_items_line_17d", ["17d Other items and amounts"], value_type="currency", optional=True),
            FormFieldDefinition("k_income_reconciliation_line_18", ["18 Income (loss) reconciliation"], value_type="currency", optional=True),

            # Schedule L (Page 4) - Balance Sheets
            # Assets
            FormFieldDefinition("sch_l_cash_line_1_begin", ["1 Cash"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_cash_line_1_end", ["1 Cash"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_trade_notes_line_2a_begin", ["2a Trade notes and accounts receivable"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_trade_notes_line_2a_end", ["2a Trade notes and accounts receivable"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_bad_debts_allowance_line_2b_begin", ["b Less allowance for bad debts"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_bad_debts_allowance_line_2b_end", ["b Less allowance for bad debts"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_inventories_line_3_begin", ["3 Inventories"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_inventories_line_3_end", ["3 Inventories"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_us_gov_obligations_line_4_begin", ["4 U.S. government obligations"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_us_gov_obligations_line_4_end", ["4 U.S. government obligations"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_tax_exempt_securities_line_5_begin", ["5 Tax-exempt securities"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_tax_exempt_securities_line_5_end", ["5 Tax-exempt securities"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_current_assets_line_6_begin", ["6 Other current assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_current_assets_line_6_end", ["6 Other current assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_loans_to_shareholders_line_7_begin", ["7 Loans to shareholders"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_loans_to_shareholders_line_7_end", ["7 Loans to shareholders"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_mortgage_real_estate_loans_line_8_begin", ["8 Mortgage and real estate loans"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_mortgage_real_estate_loans_line_8_end", ["8 Mortgage and real estate loans"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_investments_line_9_begin", ["9 Other investments"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_investments_line_9_end", ["9 Other investments"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_buildings_depreciable_assets_line_10a_begin", ["10a Buildings and other depreciable assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_buildings_depreciable_assets_line_10a_end", ["10a Buildings and other depreciable assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accumulated_depreciation_line_10b_begin", ["b Less accumulated depreciation"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accumulated_depreciation_line_10b_end", ["b Less accumulated depreciation"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_depletable_assets_line_11a_begin", ["11a Depletable assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_depletable_assets_line_11a_end", ["11a Depletable assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accumulated_depletion_line_11b_begin", ["b Less accumulated depletion"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accumulated_depletion_line_11b_end", ["b Less accumulated depletion"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_land_line_12_begin", ["12 Land"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_land_line_12_end", ["12 Land"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_intangible_assets_line_13a_begin", ["13a Intangible assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_intangible_assets_line_13a_end", ["13a Intangible assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accumulated_amortization_line_13b_begin", ["b Less accumulated amortization"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accumulated_amortization_line_13b_end", ["b Less accumulated amortization"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_assets_line_14_begin", ["14 Other assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_assets_line_14_end", ["14 Other assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_total_assets_line_15_begin", ["15 Total assets"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_total_assets_line_15_end", ["15 Total assets"], value_type="currency", optional=True),
            
            # Liabilities and Equity
            FormFieldDefinition("sch_l_accounts_payable_line_16_begin", ["16 Accounts payable"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_accounts_payable_line_16_end", ["16 Accounts payable"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_mortgages_notes_under_1yr_line_17_begin", ["17 Mortgages, notes, bonds payable in less than 1 year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_mortgages_notes_under_1yr_line_17_end", ["17 Mortgages, notes, bonds payable in less than 1 year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_current_liabilities_line_18_begin", ["18 Other current liabilities"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_current_liabilities_line_18_end", ["18 Other current liabilities"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_loans_from_shareholders_line_19_begin", ["19 Loans from shareholders"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_loans_from_shareholders_line_19_end", ["19 Loans from shareholders"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_mortgages_notes_over_1yr_line_20_begin", ["20 Mortgages, notes, bonds payable in 1 year or more"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_mortgages_notes_over_1yr_line_20_end", ["20 Mortgages, notes, bonds payable in 1 year or more"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_liabilities_line_21_begin", ["21 Other liabilities"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_other_liabilities_line_21_end", ["21 Other liabilities"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_capital_stock_line_22_begin", ["22 Capital stock"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_capital_stock_line_22_end", ["22 Capital stock"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_additional_paid_in_capital_line_23_begin", ["23 Additional paid-in capital"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_additional_paid_in_capital_line_23_end", ["23 Additional paid-in capital"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_retained_earnings_line_24_begin", ["24 Retained earnings"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_retained_earnings_line_24_end", ["24 Retained earnings"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_adjustments_to_equity_line_25_begin", ["25 Adjustments to shareholders' equity"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_adjustments_to_equity_line_25_end", ["25 Adjustments to shareholders' equity"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_less_cost_treasury_stock_line_26_begin", ["26 Less cost of treasury stock"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_less_cost_treasury_stock_line_26_end", ["26 Less cost of treasury stock"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_total_liabilities_equity_line_27_begin", ["27 Total liabilities and shareholders' equity"], value_type="currency", optional=True),
            FormFieldDefinition("sch_l_total_liabilities_equity_line_27_end", ["27 Total liabilities and shareholders' equity"], value_type="currency", optional=True),

            # Schedule M-1 (Page 5)
            FormFieldDefinition("sch_m1_net_income_books_line_1", ["1 Net income (loss) per books"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_income_on_k_not_books_line_2", ["2 Income included on Schedule K"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_expenses_books_not_k_line_3", ["3 Expenses recorded on books this year not included on Schedule K"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_depreciation_line_3a", ["a Depreciation"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_travel_entertainment_line_3b", ["b Travel and entertainment"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_add_lines_1_to_3_line_4", ["4 Add lines 1 through 3"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_income_books_not_k_line_5", ["5 Income recorded on books this year not included on Schedule K"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_tax_exempt_interest_line_5a", ["a Tax-exempt interest"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_deductions_k_not_books_line_6", ["6 Deductions included on Schedule K"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_depreciation_line_6a", ["a Depreciation"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_add_lines_5_and_6_line_7", ["7 Add lines 5 and 6"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m1_income_reconciliation_line_8", ["8 Income (loss) (Schedule K, line 18)"], value_type="currency", optional=True),

            # Schedule M-2 (Page 5)
            FormFieldDefinition("sch_m2_balance_beginning_line_1_col_a", ["1 Balance at beginning of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_beginning_line_1_col_b", ["1 Balance at beginning of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_beginning_line_1_col_c", ["1 Balance at beginning of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_beginning_line_1_col_d", ["1 Balance at beginning of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_ordinary_income_line_2_col_a", ["2 Ordinary income from page 1"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_ordinary_income_line_2_col_b", ["2 Ordinary income from page 1"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_ordinary_income_line_2_col_c", ["2 Ordinary income from page 1"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_ordinary_income_line_2_col_d", ["2 Ordinary income from page 1"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_additions_line_3_col_a", ["3 Other additions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_additions_line_3_col_b", ["3 Other additions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_additions_line_3_col_c", ["3 Other additions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_additions_line_3_col_d", ["3 Other additions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_loss_line_4_col_a", ["4 Loss from page 1, line 22"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_loss_line_4_col_b", ["4 Loss from page 1, line 22"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_loss_line_4_col_c", ["4 Loss from page 1, line 22"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_loss_line_4_col_d", ["4 Loss from page 1, line 22"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_reductions_line_5_col_a", ["5 Other reductions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_reductions_line_5_col_b", ["5 Other reductions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_reductions_line_5_col_c", ["5 Other reductions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_other_reductions_line_5_col_d", ["5 Other reductions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_combine_line_6_col_a", ["6 Combine lines 1 through 5"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_combine_line_6_col_b", ["6 Combine lines 1 through 5"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_combine_line_6_col_c", ["6 Combine lines 1 through 5"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_combine_line_6_col_d", ["6 Combine lines 1 through 5"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_distributions_line_7_col_a", ["7 Distributions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_distributions_line_7_col_b", ["7 Distributions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_distributions_line_7_col_c", ["7 Distributions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_distributions_line_7_col_d", ["7 Distributions"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_end_line_8_col_a", ["8 Balance at end of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_end_line_8_col_b", ["8 Balance at end of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_end_line_8_col_c", ["8 Balance at end of tax year"], value_type="currency", optional=True),
            FormFieldDefinition("sch_m2_balance_end_line_8_col_d", ["8 Balance at end of tax year"], value_type="currency", optional=True),
        ],
        extraction_tier=ExtractionTier.PDFPLUMBER,

    ),

    # ------------------------------------------------------------------
    # Form 1120  (C-Corp Return)
    # ------------------------------------------------------------------
    "1120": FormSchema(
        form_id="1120",
        display_name="Form 1120 (U.S. Corporation Income Tax Return)",
        detection_patterns=[
            r"Form 1120\b(?!-S)",
            "U.S. Corporation Income Tax Return",
        ],
        fields=[
            FormFieldDefinition("ein",
                ["EIN", "Employer identification number"],
                value_type="ssn"),
            FormFieldDefinition("gross_receipts_line_1a",
                ["1a Gross receipts", "Gross receipts or sales"],
                value_type="currency"),
            FormFieldDefinition("total_income_line_11",
                ["11 Total income"], value_type="currency"),
            FormFieldDefinition("total_deductions_line_27",
                ["27 Total deductions"], value_type="currency", optional=True),
            FormFieldDefinition("taxable_income_line_30",
                ["30 Taxable income"], value_type="currency"),
            FormFieldDefinition("total_tax_line_31",
                ["31 Total tax"], value_type="currency", optional=True),
        ],
        extraction_tier=ExtractionTier.PDFPLUMBER,
    ),
}


def get_form_schema(form_id: str) -> FormSchema | None:
    return FORM_REGISTRY.get(form_id)


def all_form_schemas() -> List[FormSchema]:
    return list(FORM_REGISTRY.values())
