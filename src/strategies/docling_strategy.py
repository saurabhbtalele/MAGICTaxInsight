import json
import logging
from typing import Any, Dict
from pathlib import Path

from docling.document_converter import DocumentConverter

from src.models.document import ParsedDocument
from src.strategies.base import IExtractionStrategy
from src.forms.registry import FormSchema, get_form_schema

logger = logging.getLogger(__name__)


class DoclingExtractionStrategy(IExtractionStrategy):
    """
    Tier 1 strategy: Uses IBM Docling for layout-aware MD/JSON extraction 
    and applies heuristics/regex on top of the structured representation.
    """

    def __init__(self):
        super().__init__()
        self.doc_converter = DocumentConverter()

    @property
    def tier_name(self) -> str:
        return "docling"

    def can_handle(self, form_id: str) -> bool:
        """Docling strategy can potentially handle any form, but specifically
        targeted models will prioritize it."""
        return True

    def extract(self, form_id: str, document: ParsedDocument, page_numbers: list[int]) -> Dict[str, Any]:
        schema = get_form_schema(form_id)
        if not schema:
            logger.error(f"No schema found for form_id: {form_id}")
            return {}

        pdf_path = document.metadata.get("source_path")
        if not pdf_path or not Path(pdf_path).exists():
            logger.error(f"Valid PDF path required for Docling. Passed: {pdf_path}")
            return {}

        try:
            logger.info(f"Processing with Docling: {pdf_path}")
            result = self.doc_converter.convert(pdf_path)
            docling_data = result.document.export_to_dict()
            
            # Simple fallback to trying to parse out standard labels
            extracted = self._extract_from_docling_dict(docling_data, schema)
            
            return extracted
        except Exception as e:
            logger.exception(f"Docling extraction failed: {e}")
            return {}

    def _extract_from_docling_dict(self, docling_dict: dict, schema: FormSchema) -> dict:
        """
        Attempts to map Docling structured data against our FormSchema.
        """
        results = {}
        
        # Naive first pass: just stringify everything and use docling's output 
        # like high quality OCR. 
        # A more sophisticated parser would walk the docling AST (docling_dict['texts'], docling_dict['tables']).
        
        # Flatten all text elements into a list for simple searching
        texts = []
        for item in docling_dict.get('texts', []):
            if isinstance(item, dict) and 'text' in item:
                texts.append(item['text'])
                
        full_text = " \n ".join(texts)
        
        for field in schema.fields:
            value = self._match_field(field, full_text)
            if value is not None:
                 results[field.name] = value

        return results

    def _match_field(self, field, full_text: str) -> Any:
        """
        Very simple fallback matcher using the docling text stream. 
        Currently just a stub that attempts to find the field labels and capture next words. 
        """
        # We need a more sophisticated matcher for production that anchors against 
        # bounding boxes or docling's layout structure.
        return None
