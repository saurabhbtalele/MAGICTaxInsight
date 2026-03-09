# ADR-0001: Use Docling + LLM Hybrid Extraction for Tax Forms

## Status

Proposed

## Context

Magic Tax Insight currently uses `pdfplumber` (digital PDFs) and Tesseract OCR (scanned images), followed by regex-based parsers. This works for simple forms (W-2, 1099-NEC) but struggles with:

1. **Complex table layouts**: K-1, 1065, 1120-S have multi-column tabular data.
2. **OCR noise**: Scanned documents produce fragmented text that breaks regex.
3. **Maintenance burden**: Each form needs hundreds of hand-tuned regex patterns.
4. **No layout awareness**: pdfplumber extracts raw text without understanding document structure.

## Decision Drivers

- **Accuracy** on financial data (must be high).
- **Local execution** for sensitive tax documents (no mandatory cloud dependency).
- **Table extraction** quality (many tax forms are primarily tables).
- **Maintainability** (minimize per-form regex maintenance).
- **Cost** (avoid per-document API charges for the common path).

## Considered Options

### Option 1: Enhanced Rule-Based (Regex + pdfplumber coordinate extraction)

- **Pros**: Fully local, no cost, already partially implemented.
- **Cons**: Extremely fragile, high maintenance, no layout understanding, poor OCR handling.

### Option 2: Azure Document Intelligence (Prebuilt + Custom)

- **Pros**: State-of-the-art for covered forms, handles OCR natively.
- **Cons**: No prebuilt models for K-1, 1065, 1120-S. Training custom models is expensive and time-consuming. Hard vendor lock-in.

### Option 3: Pure LLM (Gemini / Claude vision + tool calling)

- **Pros**: Handles any layout, zero training, semantic understanding.
- **Cons**: $0.01–$0.10 per document, requires API access, latency, not suitable as sole dependency.

### Option 4: Docling (IBM Research) + LLM Fallback ← **SELECTED**

- **Pros**:
  - **Free, local, open-source** (Apache 2.0 license).
  - **DocLayNet** AI model for page layout analysis.
  - **TableFormer** AI model for table structure recognition (97.9% accuracy).
  - **Multi-OCR**: EasyOCR, Tesseract, RapidOCR — no single OCR dependency.
  - **Structured output**: JSON, Markdown, HTML from any PDF (digital or scanned).
  - LLM used only as fallback when Docling confidence < 0.80.
- **Cons**: Heavier install footprint (~1 GB for models). Slower than raw pdfplumber on simple digital PDFs.

## Decision

Implement a **3-tier hybrid extraction architecture**:

1. **Tier 1 — Docling** (primary): Layout-aware, table-aware, OCR-capable local extraction.
2. **Tier 2 — LLM Fallback** (optional): Gemini 2.0 Flash for low-confidence or complex edge cases.
3. **Tier 3 — Local Regex** (legacy): Existing pdfplumber parsers remain as lightweight fallback for simple digital forms.

## Consequences

### Positive

- **Superior table extraction** for K-1, 1065, Schedules — the hardest forms.
- **Unified OCR path** — Docling handles both digital and scanned PDFs transparently.
- **Lower maintenance** — less regex to write and maintain for new forms.
- **Local-first** — no API keys required for the primary extraction path.
- **LLM only when needed** — cost-efficient and privacy-respecting.

### Negative

- **Larger install footprint** (~1 GB for Docling's AI models).
- **New dependency** to manage (Docling is actively developed but relatively new).
- **Learning curve** for the team to work with Docling's API.

### Risks

- Docling's table extraction may not perfectly handle all IRS form variants.  
  **Mitigation**: LLM fallback + existing regex parsers still available.
- Docling package size may be a concern for containerized deployments.  
  **Mitigation**: Use selective model loading; only load OCR models when scanned pages detected.

## Related Decisions

- ADR-0002 (future): Confidence-gated routing thresholds
- ADR-0003 (future): LLM provider selection (Gemini vs Claude vs local models)
