from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Tuple, Optional
from src.models.document import ParsedDocument

class IFormParser(ABC):
    @abstractmethod
    def extract(self, document: ParsedDocument, page_numbers: List[int]) -> Dict[str, Any]:
        """
        Extract fields from the specified pages of the document.
        Returns a dictionary of raw extracted values.
        """
        pass

_PARSER_REGISTRY: Dict[Tuple[str, Optional[int]], Type[IFormParser]] = {}

def register_parser(form_id: str, year: Optional[int] = None):
    """Decorator to register a parser for a specific form_id and optional year."""
    def decorator(cls: Type[IFormParser]):
        _PARSER_REGISTRY[(form_id, year)] = cls
        return cls
    return decorator


def get_form_parser(form_id: str, year: Optional[int] = None) -> Optional[Type[IFormParser]]:
    """Retrieve a parser class for a form. Falls back if exact year is missing."""
    if (form_id, year) in _PARSER_REGISTRY:
        return _PARSER_REGISTRY[(form_id, year)]
    
    # Fallback to a parser with no year specified, or the latest available year
    parsers_for_form = [
        (y, parser) for (f_id, y), parser in _PARSER_REGISTRY.items() if f_id == form_id
    ]
    if not parsers_for_form:
        return None
    
    # Prefer exact `None` fallback first if looking for a generic
    for y, parser in parsers_for_form:
        if y is None:
             return parser

    # Otherwise sort by highest year descending
    parsers_for_form.sort(key=lambda x: x[0] if x[0] is not None else -1, reverse=True)
    return parsers_for_form[0][1]
