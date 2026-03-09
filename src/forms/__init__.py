import src.forms.schemas # Ensure schemas are loaded
import src.parsers       # Ensure parsers are loaded
from .registry import FormFieldDefinition, FormSchema, all_form_schemas, get_form_schema
from .detector import DetectedForm, detect_forms
from .extractor import extract_forms

__all__ = [
    "all_form_schemas",
    "get_form_schema",
    "FormFieldDefinition",
    "FormSchema",
    "DetectedForm",
    "detect_forms",
    "extract_forms",
]

