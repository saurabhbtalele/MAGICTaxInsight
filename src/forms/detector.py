from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.forms.registry import FormSchema, all_form_schemas, get_form_schema
from src.models.document import ParsedDocument


@dataclass
class DetectedForm:
    form_id: str
    display_name: str
    page_numbers: List[int]
    confidence: float
    tax_year: int | None = None


import re

# Regex to find a 4-digit tax year (2018-2029) near the top of a page
_YEAR_RE = re.compile(r'\b(20(?:1[89]|2[0-9]))\b')

def _detect_tax_year(page_texts: list[str]) -> int | None:
    """Scan the top portion of matched pages to find the tax year."""
    for text in page_texts:
        # Only scan top ~30% of the text (header area of IRS forms)
        top_portion = text[:max(len(text) // 3, 200)]
        m = _YEAR_RE.search(top_portion)
        if m:
            return int(m.group(1))
    return None

def _page_matches_schema(page_text: str, schema: FormSchema) -> bool:
    """Check if page text matches any of the schema's patterns (supports regex)."""
    text = page_text.lower()
    for pattern in schema.detection_patterns:
        # If it looks like a regex form (e.g. contains \b or ^), use re.search
        if "\\" in pattern or "^" in pattern or "$" in pattern:
             if re.search(pattern.lower(), text, re.IGNORECASE):
                 return True
        elif pattern.lower() in text:
            return True
    return False


def detect_forms(document: ParsedDocument) -> List[DetectedForm]:
    """Detect known IRS forms (W-2, 1040, 1099-NEC, etc.) in a ParsedDocument."""
    schemas = all_form_schemas()
    detected: dict[str, DetectedForm] = {}

    for page in document.pages:
        text = page.full_text
        if not text:
            continue

        for schema in schemas:
            if _page_matches_schema(text, schema):
                existing = detected.get(schema.form_id)
                if existing:
                    existing.page_numbers.append(page.page_number)
                    # Slightly increase confidence for multi-page matches
                    existing.confidence = min(existing.confidence + 5.0, 100.0)
                else:
                    detected[schema.form_id] = DetectedForm(
                        form_id=schema.form_id,
                        display_name=schema.display_name,
                        page_numbers=[page.page_number],
                        confidence=80.0,
                        tax_year=None,  # Will be resolved after loop
                    )

    # Filename heuristics: if text detection found nothing, guess from filename.
    filename_lower = document.filename.lower()
    if not detected:
        _filename_hints: list[tuple[list[str], str]] = [
            (["w2", "w-2"],        "W-2"),
            (["1099nec", "1099-nec", "nec"],  "1099-NEC"),
            (["1099r", "1099-r"],  "1099-R"),
            (["1040"],             "1040"),
            (["schc", "schedule-c", "schedule_c"], "Schedule C (1040)"),
            (["1120s", "1120-s"],   "1120-S"),
            (["1120", "f1120"],     "1120"),
            (["k1-1120s", "k1s"],   "K-1 (1120-S)"),
        ]
        for keywords, form_id in _filename_hints:
            if any(kw in filename_lower for kw in keywords):
                schema = get_form_schema(form_id)
                if schema:
                    detected[form_id] = DetectedForm(
                        form_id=form_id,
                        display_name=schema.display_name,
                        page_numbers=[p.page_number for p in document.pages],
                        confidence=70.0,
                    )
                break

    # Resolve tax_year for each detected form
    for det in detected.values():
        page_texts = [
            p.full_text for p in document.pages if p.page_number in det.page_numbers
        ]
        det.tax_year = _detect_tax_year(page_texts)

    return list(detected.values())
