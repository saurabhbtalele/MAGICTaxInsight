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


def _page_matches_schema(page_text: str, schema: FormSchema) -> bool:
    lower = page_text.lower()
    return any(pattern.lower() in lower for pattern in schema.detection_patterns)


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
                    )

    # Filename heuristics: if text detection found nothing, guess from filename.
    filename_lower = document.filename.lower()
    if not detected:
        _filename_hints: list[tuple[list[str], str]] = [
            (["w2", "w-2"],        "W-2"),
            (["1099nec", "1099-nec", "nec"],  "1099-NEC"),
            (["1099r", "1099-r"],  "1099-R"),
            (["1040"],             "1040"),
            (["schc", "schedule-c", "schedule_c"], "Schedule C"),
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

    return list(detected.values())

