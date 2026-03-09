import pytest
from src.parsers.base_parser import _PARSER_REGISTRY, get_form_parser
from src.forms.registry import _SCHEMA_REGISTRY, get_form_schema
from src.parsers.f1120s.parser_2023 import Form1120SParser2023
import src.forms # Trigger registration

def test_registry_registration():
    """Verify that the 1120-S 2023 parser and schema are correctly registered."""
    assert ("1120-S", 2023) in _SCHEMA_REGISTRY
    assert ("1120-S", 2023) in _PARSER_REGISTRY
    assert _PARSER_REGISTRY[("1120-S", 2023)] == Form1120SParser2023

def test_routing_exact_match():
    """Verify routing when an exact year match exists."""
    parser_cls = get_form_parser("1120-S", 2023)
    assert parser_cls == Form1120SParser2023

def test_routing_fallback_higher_year():
    """Verify routing falls back to the latest available year (2023) for a higher requested year (2025)."""
    parser_cls = get_form_parser("1120-S", 2025)
    assert parser_cls == Form1120SParser2023, "Should fall back to the 2023 parser for 2025 if 2025 isn't registered."

def test_routing_no_match():
    """Verify routing returns None for a non-existent form."""
    parser_cls = get_form_parser("NON_EXISTENT_FORM", 2023)
    assert parser_cls is None

def test_schema_retrieval_integer_year():
    """Verify that schemas can be retrieved using integer years."""
    schema = get_form_schema("1120-S") # Should match default or latest
    assert schema is not None
    assert schema.form_id == "1120-S"
