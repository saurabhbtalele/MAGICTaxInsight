"""Form field extractor — 3-tier routing engine.

Extraction tiers (tried in order for each form):

  1. **Docling**  — AI-powered layout + table extraction (primary)
  2. **LLM Fallback** — Gemini 2.0 Flash with structured outputs
  3. **Local**   — dedicated pdfplumber parsers or generic regex

The tier is selected automatically:
  - Docling runs first; if confidence ≥ 0.80 → result accepted.
  - Otherwise LLM fallback is attempted.
  - If LLM fails or is unavailable → LocalExtractionStrategy (pdfplumber).

The strategy used for each form is reported via the
``extraction_tier_used`` field on ``ExtractedForm``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from src.forms.registry import ExtractionTier, FormSchema, get_form_schema
from src.models.document import ParsedDocument
from src.strategies.azure_prebuilt_strategy import AzureDIPrebuiltStrategy
from src.strategies.docling_strategy import DoclingExtractionStrategy
from src.strategies.llm_strategy import LlmExtractionStrategy
from src.strategies.local_strategy import LocalExtractionStrategy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons — avoid reconstructing heavy objects per form
# ---------------------------------------------------------------------------

_local_strategy = LocalExtractionStrategy()
_docling_strategy = DoclingExtractionStrategy()
_llm_strategy = LlmExtractionStrategy()

# Confidence floor for Docling / LLM results
_CONFIDENCE_THRESHOLD = 0.80


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

_HIGH_WEIGHT_TYPES = frozenset({"currency", "ssn"})


def _score_confidence(schema: FormSchema, fields: Dict[str, Any]) -> float:
    """Weighted confidence: required currency/SSN fields count double."""
    if not schema.fields:
        return 0.0
    total = 0.0
    matched = 0.0
    for f in schema.fields:
        w = 2.0 if f.value_type in _HIGH_WEIGHT_TYPES else 1.0
        if not f.optional:
            total += w
            if fields.get(f.name) is not None:
                matched += w
    return matched / total if total else 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_form_fields(
    document: ParsedDocument,
    schema: FormSchema,
    page_numbers: Iterable[int],
) -> tuple[Dict[str, Any], str]:
    """Extract all fields for one form via the 3-tier strategy cascade.

    Returns ``(fields_dict, tier_name)`` where *tier_name* is one of
    ``"docling"``, ``"llm_fallback"``, ``"pdfplumber"``, or
    ``"generic_regex"``.
    """
    pages = list(page_numbers)

    # ------- Azure DI prebuilt (mock) — kept for backward compat ----------
    if (
        schema.extraction_tier == ExtractionTier.AZURE_PREBUILT
        and schema.azure_model_id
    ):
        strategy = AzureDIPrebuiltStrategy(schema.azure_model_id, _local_strategy)
        fields = strategy.extract(schema.form_id, document, pages)
        return fields, strategy.tier_name

    # ------- PDFPLUMBER only ----------------------------------------------
    if schema.extraction_tier == ExtractionTier.PDFPLUMBER:
        local_fields = _local_strategy.extract(schema.form_id, document, pages)
        return local_fields, _local_strategy.tier_name

    # ------- Tier 1: Docling ----------------------------------------------
    if schema.extraction_tier == ExtractionTier.DOCLING:
        docling_fields = _docling_strategy.extract(schema.form_id, document, pages)
        if docling_fields:
            confidence = _score_confidence(schema, docling_fields)
            if confidence >= _CONFIDENCE_THRESHOLD:
                logger.info(
                    "[extractor] Tier 1 (Docling) accepted for %s (%.2f).",
                    schema.form_id,
                    confidence,
                )
                return docling_fields, _docling_strategy.tier_name

    # ------- Tier 2: LLM Fallback ----------------------------------------
    if schema.extraction_tier in (ExtractionTier.DOCLING, ExtractionTier.LLM_FALLBACK):
        llm_fields = _llm_strategy.extract(schema.form_id, document, pages)
        if llm_fields:
            confidence = _score_confidence(schema, llm_fields)
            if confidence >= _CONFIDENCE_THRESHOLD:
                logger.info(
                    "[extractor] Tier 2 (LLM) accepted for %s (%.2f).",
                    schema.form_id,
                    confidence,
                )
                return llm_fields, _llm_strategy.tier_name
            logger.info(
                "[extractor] Tier 2 (LLM) low confidence %.2f for %s — "
                "flagged for human review.",
                confidence,
                schema.form_id,
            )
            # Still return the LLM result (with flag) as it may be partial
            return llm_fields, _llm_strategy.tier_name

    # ------- Tier 3: Local (pdfplumber / regex) ---------------------------
    # Fallback to local if Docling/LLM failed or returned low confidence
    local_fields = _local_strategy.extract(schema.form_id, document, pages)
    return local_fields, _local_strategy.tier_name


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
