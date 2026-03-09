import json
import logging
from typing import Any, Dict

from google import genai

from src.models.document import ParsedDocument
from src.strategies.base import IExtractionStrategy
from src.forms.registry import FormSchema, get_form_schema

logger = logging.getLogger(__name__)

class LlmExtractionStrategy(IExtractionStrategy):
    """
    Tier 2 strategy: Uses a configured LLM (e.g. Gemini) to extract structured
    JSON given the raw text of the document and the target FormSchema.
    """

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key
        try:
             self.client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        except Exception as e:
             logger.warning(f"Could not initialize GenAI client: {e}")
             self.client = None


    @property
    def tier_name(self) -> str:
        return "llm"

    def can_handle(self, form_id: str) -> bool:
        return True

    def extract(self, form_id: str, document: ParsedDocument, page_numbers: list[int]) -> Dict[str, Any]:
        if not self.client:
             logger.error("GenAI Client not initialized, skipping LLM strategy.")
             return {}

        schema = get_form_schema(form_id)
        if not schema:
            return {}

        prompt = self._build_prompt(document.text, schema)
        
        try:
            logger.info("Calling LLM for extraction...")
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            
            return self._parse_json_from_response(response.text)
        except Exception as e:
            logger.exception(f"LLM extraction failed: {e}")
            return {}

    def _build_prompt(self, text: str, schema: FormSchema) -> str:
        fields_str = ", ".join([f.name for f in schema.fields])
        
        prompt = f"""
You are a tax extraction assistant. Your job is to extract values from the following tax document text 
into a structured JSON format according to the requested schema.

Form: {schema.display_name}
Requested fields: {fields_str}

Please output ONLY valid JSON. If a value is missing, use null.
"""
        prompt += f"\n\n--- DOCUMENT TEXT ---\n{text}\n--- END DOCUMENT TEXT ---\n"
        return prompt

    def _parse_json_from_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
             text = text[7:]
        if text.startswith("```"):
             text = text[3:]
        if text.endswith("```"):
             text = text[:-3]
             
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from LLM response.")
            return {}
