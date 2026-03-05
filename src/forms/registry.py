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
}


def get_form_schema(form_id: str) -> FormSchema | None:
    return FORM_REGISTRY.get(form_id)


def all_form_schemas() -> List[FormSchema]:
    return list(FORM_REGISTRY.values())
