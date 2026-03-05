"""Form field extractor.

This module now delegates extraction to strategy implementations:

  - LocalExtractionStrategy — wraps existing dedicated parsers and
    generic regex fallback for unsupported forms.
  - AzureDIPrebuiltStrategy — MOCK strategy that logs which Azure
    Document Intelligence model would be called, then delegates to
    LocalExtractionStrategy.

The strategy used for each form is reported via the
`extraction_tier_used` field on ExtractedForm.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.forms.registry import ExtractionTier, FormSchema, get_form_schema
from src.models.document import ParsedDocument
from src.strategies.azure_prebuilt_strategy import AzureDIPrebuiltStrategy
from src.strategies.local_strategy import LocalExtractionStrategy


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_form_fields(
    document: ParsedDocument,
    schema: FormSchema,
    page_numbers: Iterable[int],
) -> tuple[Dict[str, Any], str]:
    """Extract all fields for one form via the configured strategy.

    The strategy is chosen based on FormSchema.extraction_tier:

      - ExtractionTier.AZURE_PREBUILT: use AzureDIPrebuiltStrategy (MOCK)
        which logs the intended Azure DI call and delegates to the local
        strategy for actual extraction.
      - All other tiers: use LocalExtractionStrategy directly.
    """
    local_strategy = LocalExtractionStrategy()

    if (
        schema.extraction_tier == ExtractionTier.AZURE_PREBUILT
        and schema.azure_model_id
    ):
        strategy = AzureDIPrebuiltStrategy(schema.azure_model_id, local_strategy)
    else:
        strategy = local_strategy

    fields = strategy.extract(schema.form_id, document, list(page_numbers))
    return fields, strategy.tier_name


def extract_forms(
    document: ParsedDocument,
    detected_forms: List[Any],
) -> List[Dict[str, Any]]:
    """Extract fields for every detected form; returns a list of result dicts."""
    extracted: List[Dict[str, Any]] = []
    for detected in detected_forms:
        schema = get_form_schema(detected.form_id)
        if not schema:
            continue
        fields, tier_name = extract_form_fields(
            document,
            schema,
            detected.page_numbers,
        )
        extracted.append({
            "form_id": detected.form_id,
            "display_name": detected.display_name,
            "page_numbers": detected.page_numbers,
            "confidence": detected.confidence,
            "fields": fields,
            "extraction_tier_used": tier_name,
        })
    return extracted
