from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ExtractionTier(Enum):
    PDFPLUMBER = "pdfplumber"
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
        extraction_tier=ExtractionTier.AZURE_PREBUILT,
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
        extraction_tier=ExtractionTier.AZURE_PREBUILT,
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
        extraction_tier=ExtractionTier.AZURE_PREBUILT,
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
        extraction_tier=ExtractionTier.AZURE_PREBUILT,
    ),

    # ------------------------------------------------------------------
    # Schedule C
    # ------------------------------------------------------------------
    "Schedule C": FormSchema(
        form_id="Schedule C",
        display_name="Schedule C (Profit or Loss From Business)",
        detection_patterns=[
            "Schedule C",
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
        extraction_tier=ExtractionTier.AZURE_PREBUILT,
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
    # No Azure DI prebuilt model exists; dedicated pdfplumber parser used.
    # ------------------------------------------------------------------
    "K-1 (1120-S)": FormSchema(
        form_id="K-1 (1120-S)",
        display_name="Schedule K-1 (Form 1120-S) — Shareholder's Share of Income",
        detection_patterns=[
            "K-1 (Form 1120-S)",
            "Shareholder's Share of Income",
            "Shareholder's share of income",
            "(Form 1120-S)",
            "1120-S",
        ],
        fields=[
            FormFieldDefinition("s_corp_ein",
                ["Corporation's employer identification number", "Corporation EIN"],
                value_type="str", optional=True),
            FormFieldDefinition("s_corp_name",
                ["Corporation's name", "Name of corporation", "S corporation name"],
                value_type="str", optional=True),
            FormFieldDefinition("shareholder_tin",
                ["Shareholder's identifying number", "Shareholder's SSN or TIN"],
                value_type="str", optional=True),
            FormFieldDefinition("shareholder_name",
                ["Shareholder's name"], value_type="str", optional=True),
            FormFieldDefinition("ownership_percentage",
                ["G Shareholder's percentage of stock ownership",
                 "Percentage of stock ownership"],
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
            FormFieldDefinition("interest_income_box_4",
                ["4 Interest income"], value_type="currency", optional=True),
            FormFieldDefinition("ordinary_dividends_box_5a",
                ["5a Ordinary dividends", "5 Ordinary dividends"],
                value_type="currency", optional=True),
            FormFieldDefinition("qualified_dividends_box_5b",
                ["5b Qualified dividends"], value_type="currency", optional=True),
            FormFieldDefinition("royalties_box_6",
                ["6 Royalties"], value_type="currency", optional=True),
            FormFieldDefinition("net_short_term_capital_gain_loss_box_7",
                ["7 Net short-term capital gain (loss)"],
                value_type="currency", optional=True),
            FormFieldDefinition("net_long_term_capital_gain_loss_box_8a",
                ["8a Net long-term capital gain (loss)", "8 Net long-term capital gain"],
                value_type="currency", optional=True),
            FormFieldDefinition("net_section_1231_gain_loss_box_9",
                ["9 Net section 1231 gain (loss)"],
                value_type="currency", optional=True),
            FormFieldDefinition("other_income_loss_box_10",
                ["10 Other income (loss)"], value_type="currency", optional=True),
            FormFieldDefinition("section_179_deduction_box_11",
                ["11 Section 179 deduction"], value_type="currency", optional=True),
            FormFieldDefinition("distributions_box_16",
                ["16 Items affecting shareholder basis",
                 "16D Cash and property distributions", "16D Distributions"],
                value_type="currency", optional=True),
        ],
        extraction_tier=ExtractionTier.PDFPLUMBER,
    ),
}


def get_form_schema(form_id: str) -> FormSchema | None:
    return FORM_REGISTRY.get(form_id)


def all_form_schemas() -> List[FormSchema]:
    return list(FORM_REGISTRY.values())
