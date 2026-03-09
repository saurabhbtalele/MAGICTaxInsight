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


_SCHEMA_REGISTRY: Dict[tuple[str, int | None], FormSchema] = {}

def register_schema(form_id: str, year: int | None = None):
    """Decorator to register a FormSchema to the global registry by form_id and year."""
    def decorator(schema_func):
        schema = schema_func()
        _SCHEMA_REGISTRY[(form_id, year)] = schema
        return schema_func
    return decorator


def get_form_schema(form_id: str, year: int | None = None) -> FormSchema | None:
    """Retrieve a schema. If the exact year isn't found, try finding any schema for that form."""
    if (form_id, year) in _SCHEMA_REGISTRY:
        return _SCHEMA_REGISTRY[(form_id, year)]
    
    # Fallback to a schema with no year specified, or the latest available year
    schemas_for_form = [
        (y, schema) for (f_id, y), schema in _SCHEMA_REGISTRY.items() if f_id == form_id
    ]
    if not schemas_for_form:
        return None
    
    # Prefer exact `None` fallback first if looking for a generic
    for y, schema in schemas_for_form:
        if y is None:
             return schema

    # Otherwise sort by highest year descending
    schemas_for_form.sort(key=lambda x: x[0] if x[0] is not None else 0, reverse=True)
    return schemas_for_form[0][1]


def all_form_schemas() -> List[FormSchema]:
    return list(_SCHEMA_REGISTRY.values())

# ------------------------------------------------------------------
# Legacy Hardcoded Registrations (to be modularized)
# ------------------------------------------------------------------

@register_schema("W-2", 2023)
def _schema_w2_2023():
    return FormSchema(
        form_id="W-2",
        display_name="Form W-2 (Wage and Tax Statement)",
        detection_patterns=["Form W-2", "Wage and Tax Statement", "Employee's SSA number"],
        fields=[
            FormFieldDefinition("employee_ssn", ["Employee's SSA number", "Employee's social security number"], value_type="ssn"),
            FormFieldDefinition("employer_ein", ["Employer's FED ID number", "Employer identification number", "EIN"], value_type="ssn"),
            FormFieldDefinition("employee_name", ["Employee's name"], value_type="str", optional=True),
            FormFieldDefinition("employer_name", ["Employer's name"], value_type="str", optional=True),
            FormFieldDefinition("wages_tips_other_compensation_box_1", ["Wages, tips, other comp.", "1 Wages, tips, other compensation"], value_type="currency"),
            FormFieldDefinition("federal_income_tax_withheld_box_2", ["Federal income tax withheld", "2 Federal income tax withheld"], value_type="currency"),
        ],
        azure_model_id="tax.us.w2", 
        extraction_tier=ExtractionTier.DOCLING,
    )

@register_schema("1099-NEC", 2023)
def _schema_1099nec():
    return FormSchema(
        form_id="1099-NEC", display_name="Form 1099-NEC (Nonemployee Compensation)",
        detection_patterns=["Form 1099-NEC", "Nonemployee compensation"],
        fields=[
             FormFieldDefinition("payer_tin", ["PAYER'S TIN", "Payer's TIN"], value_type="ssn"),
             FormFieldDefinition("recipient_tin", ["RECIPIENT'S TIN", "Recipient's TIN"], value_type="ssn"),
             FormFieldDefinition("nonemployee_compensation_box_1", ["1 Nonemployee compensation", "Nonemployee compensation"], value_type="currency"),
        ], azure_model_id="tax.us.1099NEC.2023", extraction_tier=ExtractionTier.DOCLING)

@register_schema("1040", 2023)
def _schema_1040():
    return FormSchema(
        form_id="1040", display_name="Form 1040 (U.S. Individual Income Tax Return)", detection_patterns=["Form 1040", "U.S. Individual Income Tax Return"],
        fields=[
            FormFieldDefinition("adjusted_gross_income_line_11", ["11 Adjusted gross income"], value_type="currency"),
            FormFieldDefinition("taxable_income_line_15", ["15 Taxable income"], value_type="currency"),
            FormFieldDefinition("total_tax_line_24", ["24 Total tax"], value_type="currency"),
        ], azure_model_id="tax.us.1040.2023", extraction_tier=ExtractionTier.DOCLING)

@register_schema("1120", 2023)
def _schema_1120():
    return FormSchema(
        form_id="1120", display_name="Form 1120 (U.S. Corporation Income Tax Return)", detection_patterns=[r"Form 1120\b(?!-S)", "U.S. Corporation Income Tax Return"],
        fields=[
             FormFieldDefinition("ein", ["EIN", "Employer identification number"], value_type="ssn"),
             FormFieldDefinition("total_income_line_11", ["11 Total income"], value_type="currency"),
             FormFieldDefinition("taxable_income_line_30", ["30 Taxable income"], value_type="currency"),
        ], extraction_tier=ExtractionTier.PDFPLUMBER)

@register_schema("K-1 (1065)", 2023)
def _schema_k1_1065():
    return FormSchema(
        form_id="K-1 (1065)", display_name="Schedule K-1 (Form 1065) — Partner's Share of Income",
        detection_patterns=["Schedule K-1 (Form 1065)", "K-1 (Form 1065)"], fields=[], extraction_tier=ExtractionTier.PDFPLUMBER
    )

