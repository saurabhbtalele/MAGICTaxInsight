from __future__ import annotations

import importlib
import re
from typing import Any, Dict, Iterable

from src.forms.registry import FormFieldDefinition, FormSchema, get_form_schema
from src.models.document import ParsedDocument
from src.strategies.base import IExtractionStrategy
from src.utils.logger import log


# Maps form_id → (module, pdf_function, text_function)
# pdf_function  : called for digital PDFs — receives the file path
# text_function : called for OCR'd / pre-extracted text — receives raw text str
_DEDICATED_PARSERS: dict[str, tuple[str, str, str]] = {
    "W-2": (
        "src.parsers.w2_parser",
        "extract_w2_from_pdf",
        "extract_w2_from_text",
    ),
    "1099-NEC": (
        "src.parsers.form1099nec_parser",
        "extract_1099nec_from_pdf",
        "extract_1099nec_from_text",
    ),
    "1099-R": (
        "src.parsers.form1099r_parser",
        "extract_1099r_from_pdf",
        "extract_1099r_from_text",
    ),
    "1040": (
        "src.parsers.form1040_parser",
        "extract_1040_from_pdf",
        "extract_1040_from_text",
    ),
    "K-1 (1065)": (
        "src.parsers.k1_1065_parser",
        "extract_k1_1065_from_pdf",
        "extract_k1_1065_from_text",
    ),
    "Schedule K (1065)": (
        "src.parsers.k1_1065_parser",
        "extract_k1_1065_from_pdf",
        "extract_k1_1065_from_text",
    ),
    "K-1 (1120-S)": (
        "src.parsers.k1_1120s_parser",
        "extract_k1_1120s_from_pdf",
        "extract_k1_1120s_from_text",
    ),
    "1099-MISC": (
        "src.parsers.form1099misc_parser",
        "extract_1099misc_from_pdf",
        "extract_1099misc_from_text",
    ),
    "Schedule B (1040)": (
        "src.parsers.schedule_b_1040_parser",
        "extract_schedule_b_from_pdf",
        "extract_schedule_b_from_text",
    ),
    "Schedule C (1040)": (
        "src.parsers.schedule_c_1040_parser",
        "extract_schedule_c_from_pdf",
        "extract_schedule_c_from_text",
    ),
    "Schedule D (1040)": (
        "src.parsers.schedule_d_1040_parser",
        "extract_schedule_d_from_pdf",
        "extract_schedule_d_from_text",
    ),
    "Schedule E (1040)": (
        "src.parsers.schedule_e_1040_parser",
        "extract_schedule_e_from_pdf",
        "extract_schedule_e_from_text",
    ),
    "Schedule F (1040)": (
        "src.parsers.schedule_f_1040_parser",
        "extract_schedule_f_from_pdf",
        "extract_schedule_f_from_text",
    ),
    "1065": (
        "src.parsers.form1065_parser",
        "extract_1065_from_pdf",
        "extract_1065_from_text",
    ),
    "1120-S": (
        "src.parsers.form1120s_parser",
        "extract_1120s_from_pdf",
        "extract_1120s_from_text",
    ),
    "1120": (
        "src.parsers.form1120_parser",
        "extract_1120_from_pdf",
        "extract_1120_from_text",
    ),
}


def _join_pages(document: ParsedDocument, page_numbers: Iterable[int]) -> str:
    page_set = set(page_numbers)
    return "\n".join(p.full_text for p in document.pages if p.page_number in page_set)


def _regex_extract(pattern: str, text: str, value_type: str) -> Any:
    m = re.search(
        rf"{re.escape(pattern)}[ \t:]*([0-9A-Za-z\-/.,$() ]+)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    raw = m.group(1).strip()
    if value_type in {"currency", "float"}:
        num = re.search(r"\d[\d,]*\.?\d*", raw)
        if num:
            try:
                return float(num.group(0).replace(",", ""))
            except ValueError:
                pass
    if value_type == "int":
        num = re.search(r"\d[\d,]*", raw)
        if num:
            try:
                return int(num.group(0).replace(",", ""))
            except ValueError:
                pass
    return raw


def _regex_extract_field(field: FormFieldDefinition, text: str) -> Any:
    for label in field.label_patterns:
        value = _regex_extract(label, text, field.value_type)
        if value is not None:
            return value
    return None


def _generic_extract(
    document: ParsedDocument,
    schema: FormSchema,
    page_numbers: Iterable[int],
) -> Dict[str, Any]:
    text = _join_pages(document, page_numbers)
    results: Dict[str, Any] = {}
    for f in schema.fields:
        v = _regex_extract_field(f, text)
        if v is not None or not f.optional:
            results[f.name] = v
    return results


class LocalExtractionStrategy(IExtractionStrategy):
    """Strategy that uses existing dedicated parsers or generic regex fallback.

    This wraps the previous logic from src.forms.extractor:
      - For forms with a dedicated parser, call the PDF or text entry point
        depending on whether OCR was used.
      - For other forms, use the generic regex-based extractor over page text.
    """

    def __init__(self) -> None:
        self._last_tier_name = "generic_regex"

    @property
    def tier_name(self) -> str:
        return self._last_tier_name

    def extract(
        self,
        form_id: str,
        document: ParsedDocument,
        page_numbers: list[int],
    ) -> dict[str, Any]:
        schema = get_form_schema(form_id)
        if not schema:
            self._last_tier_name = "generic_regex"
            return {}

        entry = _DEDICATED_PARSERS.get(schema.form_id)
        if not entry:
            self._last_tier_name = "generic_regex"
            return _generic_extract(document, schema, page_numbers)

        module_name, pdf_fn, text_fn = entry
        is_ocr = bool((document.metadata or {}).get("ocr_engine"))

        try:
            mod = importlib.import_module(module_name)

            if is_ocr:
                combined_text = _join_pages(document, page_numbers)
                self._last_tier_name = "pdfplumber"
                return getattr(mod, text_fn)(combined_text)

            source_path = (document.metadata or {}).get("source_path")
            if source_path:
                self._last_tier_name = "pdfplumber"
                return getattr(mod, pdf_fn)(source_path)

        except Exception as e:
            log.warning(f"Local strategy parser failed for {schema.form_id}: {e}")
            # Fall back to generic regex extraction on any parser error.
            pass

        self._last_tier_name = "generic_regex"
        return _generic_extract(document, schema, page_numbers)

