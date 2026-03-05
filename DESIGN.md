# Magic Tax Insight — Design Document

| Field | Detail |
|---|---|
| **Version** | 1.0 |
| **Date** | March 4, 2026 |
| **Status** | Living Document |
| **Owner** | Magic Tax Insight Team |

---

## Table of Contents

1. [Project Purpose & Scope](#1-project-purpose--scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Extraction Pipeline](#3-extraction-pipeline)
4. [Form Registry Design](#4-form-registry-design)
5. [Extraction Strategy Tiers](#5-extraction-strategy-tiers)
6. [Domain Model](#6-domain-model)
7. [JSON Output Schema](#7-json-output-schema)
8. [Supported Tax Forms — Roadmap](#8-supported-tax-forms--roadmap)
9. [Project Structure](#9-project-structure)
10. [Current Implementation Status](#10-current-implementation-status)
11. [Phased Development Plan](#11-phased-development-plan)
12. [Known Limitations & Decisions](#12-known-limitations--decisions)

---

## 1. Project Purpose & Scope

### What Magic Tax Insight Does

Magic Tax Insight is a **tax form data extraction service**. Its single responsibility is:

> Accept a tax document PDF → detect which IRS forms are present → extract all structured field values → return a JSON object.

### Explicit Scope Boundaries

| In Scope | Out of Scope |
|---|---|
| Detecting IRS form types within a PDF | Income calculations |
| Extracting raw field values from each form | MGIC worksheet population |
| Normalising values (currency, SSN, dates) | Underwriting logic |
| Confidence scoring per form/field | Cross-document validation |
| Structured JSON output | Mortgage-specific business rules |
| Handling multiple forms in one PDF | LOS / CRM integration |

The consuming system (e.g. a .NET orchestration service or an MGIC calculation engine) is responsible for using the extracted data. Magic Tax Insight only extracts and returns it.

### Input / Output Contract

```
INPUT:   A PDF file path  (digital or scanned)
OUTPUT:  A structured JSON document containing all detected
         forms and their extracted field values
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                    │
│                    PDF File (any tax package)                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — TEXT EXTRACTION                                       │
│  Convert PDF pages to raw text                                   │
│  Strategy:  pdfplumber (digital)  │  Tesseract / Azure DI (OCR) │
└──────────────────────────────┬──────────────────────────────────┘
                               │  ParsedDocument (pages + raw_text)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — FORM DETECTION                                        │
│  Identify which IRS forms are present and on which pages         │
│  Strategy:  text-pattern matching against FORM_REGISTRY          │
│             + filename heuristic fallback                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │  List[DetectedForm]
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — FIELD EXTRACTION                                      │
│  For each detected form, extract all structured field values     │
│  Strategy:  dedicated parser (per form_id)                       │
│             → generic regex fallback                             │
│             → Azure DI prebuilt (future)                         │
│             → Azure DI custom / LLM (future, for K-1 / 1065)    │
└──────────────────────────────┬──────────────────────────────────┘
                               │  List[ExtractedForm]
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4 — JSON SERIALISATION                                    │
│  Normalise and emit structured JSON output                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUT                                   │
│                    Structured JSON file                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Extraction Pipeline

### Step 1 — Text Extraction (`src/tax_pipeline.py`)

Opens the PDF and produces a `ParsedDocument` containing one `ParsedPage` per PDF page, each holding the raw extracted text.

The pipeline first classifies each page using `classify_pdf_pages` from `src/utils/page_classifier.py`, which returns a `DocumentClassification` object summarising:

- Whether all pages appear to contain selectable text or images (`all_selectable`, `all_image`).
- Whether the document has a mix of text and image pages (`has_mixed_pages`).
- A per-page list of `PageClassification` entries (`page_number`, `page_type`, `char_count`, `image_area_ratio`, `confidence`).

The key document-level property is:

- `DocumentClassification.is_scanned_document` — **True only when every page appears image-based** (no embedded text). If any page has selectable text, the document is not treated as scanned overall.

Routing logic:

- If `is_scanned_document` is **True**:
  - `_build_document_ocr` is used:
    - `TesseractEngine` (`src/ocr/tesseract_engine.py`) renders each page to a 300 DPI grayscale image using PyMuPDF (`fitz`).
    - Tesseract 5 (`pytesseract`) extracts text and per-word confidences.
    - `ParsedPage.raw_text` is populated from OCR output.
    - `ParsedDocument.metadata` includes:
      - `"source_path"`
      - `"ocr_engine": "tesseract"`
      - `"ocr_page_confidences": {page_number: mean_confidence}`.
- If `is_scanned_document` is **False**:
  - `_build_document_digital` is used:
    - `pdfplumber` opens the PDF and populates `ParsedPage.raw_text` from `page.extract_text() or ""`.
    - `ParsedDocument.metadata` includes `"source_path"`.

In both cases, `_build_document` attaches page-level classification metadata:

- `"page_classification"` — the `DocumentClassification` instance.
- `"is_scanned_document"` — final document-level verdict (all-image vs not).
- `"has_mixed_pages"` — whether both `selectable_text` and `image` pages occur.
- `"page_types"` — `{ page_number: "selectable_text" | "image" }`.

### Step 2 — Form Detection (`src/forms/detector.py`)

Scans each page's text against the `detection_patterns` defined in `FORM_REGISTRY`.

- **Primary**: text-pattern match (e.g. `"Wage and Tax Statement"`, `"Form W-2"`).
- **Fallback**: filename heuristic (e.g. filename contains `w2`).
- **Confidence**: starts at 80%, increases 5% per additional matched page, capped at 100%.

Returns `List[DetectedForm]` — each with `form_id`, `display_name`, `page_numbers[]`, `confidence`.

### Step 3 — Field Extraction (`src/forms/extractor.py`)

For each `DetectedForm`, resolves the extraction strategy:

1. **Dedicated parser** — if a parser is registered in `_DEDICATED_PARSERS` for this `form_id`, it is called directly with the PDF path. This is the primary path.
2. **Generic regex fallback** — if no dedicated parser exists, uses the `label_patterns` from the `FormSchema` to attempt extraction from the raw page text.

Returns `List[ExtractedForm]` — each with `form_id`, `fields: dict[str, Any]`, `confidence`, `tax_year`, `page_numbers[]`.

### Step 4 — JSON Output (`tax_poc.py`)

Serialises all `ExtractedForm` objects to a JSON file. The root object always has the shape defined in [Section 7](#7-json-output-schema).

---

## 4. Form Registry Design

All supported forms are registered in `src/forms/registry.py` as a `FORM_REGISTRY` dict.

### `FormSchema` dataclass

```python
@dataclass
class FormSchema:
    form_id: str                          # Unique key: "W-2", "1040", "Schedule C"
    display_name: str                     # Human label
    detection_patterns: List[str]         # Text patterns that identify this form
    fields: List[FormFieldDefinition]     # All extractable fields
    parent_form_id: str | None = None     # e.g. "1040" for all Schedules
    supports_multiple_instances: bool = False  # True for Sched C, E, K-1
    extraction_tier: ExtractionTier = ExtractionTier.PDFPLUMBER
```

### `FormFieldDefinition` dataclass

```python
@dataclass
class FormFieldDefinition:
    name: str                     # Field key in JSON output
    label_patterns: List[str]     # Text labels to search for (regex-friendly)
    value_type: str               # "str" | "currency" | "ssn" | "ein" | "date" | "int" | "float"
    optional: bool = False        # If True, null in output is acceptable
```

### Adding a New Form

To add support for any new IRS form:

1. Add a `FormSchema` entry to `FORM_REGISTRY` in `registry.py`.
2. Create a dedicated parser in `src/parsers/<form_id>_parser.py`.
3. Register the parser in `_DEDICATED_PARSERS` in `extractor.py`.
4. No other files need changing — the pipeline picks it up automatically.

---

## 5. Extraction Strategy Tiers

The extraction strategy for a form is determined by `FormSchema.extraction_tier`.

```python
class ExtractionTier(Enum):
    PDFPLUMBER     = "pdfplumber"       # Digital PDFs — current approach
    AZURE_PREBUILT = "azure_prebuilt"   # Personal tax forms via Azure DI prebuilt models
    AZURE_CUSTOM   = "azure_custom"     # Business entity forms (K-1, 1065, 1120-S)
    LLM_FALLBACK   = "llm_fallback"     # Unstructured / low-confidence fallback
```

### Confidence-gated routing (future)

```
PDF
 │
 ▼  pdfplumber
 │  confidence >= 0.80? ──Yes──► Accept
 │  confidence < 0.80?  ──No──► Azure DI prebuilt
                                  │
                                  confidence >= 0.80? ──Yes──► Accept
                                  confidence < 0.80?  ──No──► LLM fallback
                                                                │
                                                                Always ──► Flag for human review
```

### Azure DI Prebuilt Model Coverage

| Form | Azure DI Model ID |
|---|---|
| Form W-2 | `tax.us.w2` |
| Form 1099-NEC | `tax.us.1099NEC.2023` |
| Form 1099-R | `tax.us.1099R.2023` |
| Form 1040 | `tax.us.1040.2023` |
| Schedule B | `tax.us.1040ScheduleB.2023` |
| Schedule C | `tax.us.1040ScheduleC.2023` |
| Schedule D | `tax.us.1040ScheduleD.2022` |
| Schedule E | `tax.us.1040ScheduleE.2023` |
| Schedule F | `tax.us.1040ScheduleF.2023` |

Forms not covered by Azure DI prebuilt (K-1, Form 1065, Form 1120-S) require a custom Azure DI model or LLM-based extraction.

---

## 6.5 MGIC Document Identification (Conceptual)

MGIC consumers often work with a predictable set of tax documents (e.g. W-2, 1099-NEC, 1099-R, 1040, Schedule C). Rather than using an LLM for document identification, Magic Tax Insight is designed to support a **rules-based, JSON-backed catalog** that maps detected IRS forms to MGIC-level document types and extractors.

### JSON-backed document catalog

A separate JSON configuration (owned by the consuming MGIC layer) can define known document types:

```json
{
  "documents": [
    {
      "id": "mgic_w2",
      "displayName": "W-2 Wage and Tax Statement",
      "irsFormIds": ["W-2"],
      "filenamePatterns": ["w2", "w-2"],
      "textPatterns": ["Wage and Tax Statement", "Form W-2"],
      "extractor": "mgic.w2_extractor"
    },
    {
      "id": "mgic_1099_nec",
      "displayName": "1099-NEC Nonemployee Compensation",
      "irsFormIds": ["1099-NEC"],
      "filenamePatterns": ["1099nec", "1099-nec"],
      "textPatterns": ["Nonemployee compensation"],
      "extractor": "mgic.nec_extractor"
    },
    {
      "id": "unknown",
      "displayName": "Unknown Document",
      "irsFormIds": [],
      "filenamePatterns": [],
      "textPatterns": [],
      "extractor": null
    }
  ]
}
```

This catalog is resolved **after** the core tax pipeline has produced a `ParsedDocument` and `DetectedForm` list.

### Identification algorithm (MGIC layer)

At a high level:

1. **Build `ParsedDocument`** using `process_tax_package` or `_build_document`:
   - The document has already been classified as scanned vs digital using `page_classifier`.
   - `ParsedDocument.metadata["is_scanned_document"]` indicates which path was used.
2. **Detect IRS forms**:
   - Call `detect_forms(document)` to get a `List[DetectedForm]` (`form_id`, `display_name`, `page_numbers`, `confidence`).
3. **Map to MGIC document type**:
   - For each `DetectedForm` (or the highest-confidence one):
     - Match `form_id` against `irsFormIds` entries in the JSON catalog.
     - Optionally refine using `filenamePatterns` (source file name) and `textPatterns` (page text).
4. **Resolve document type**:
   - If a catalog entry matches:
     - Return its `id`, `displayName`, and configured `extractor` for MGIC-specific processing.
   - If nothing matches:
     - Return the `"unknown"` entry and treat the document as unsupported / needing manual review.

This design keeps Magic Tax Insight itself **LLM-free and deterministic** for document identification, while allowing MGIC to:

- Maintain a source-of-truth document list in JSON.
- Evolve mappings without code changes in the extractor.
- Cleanly distinguish between **known** and **unknown** documents.

If the MGIC layer later requires more flexible classification (e.g. noisy or novel documents), an LLM-based classifier can be plugged in on top of this catalog, without changing the core extraction pipeline.

---

## 6. Domain Model

### `ParsedDocument`

Internal intermediate representation. Not part of the JSON output.

```python
@dataclass
class ParsedPage:
    page_number: int
    raw_text: str

@dataclass
class ParsedDocument:
    filename: str
    total_pages: int
    pages: list[ParsedPage]
    metadata: dict[str, Any]          # includes "source_path", scan/ocr metadata
    extracted_forms: list[ExtractedForm]
```

`metadata` may additionally contain:

- `"page_classification"` — the `DocumentClassification` returned by `classify_pdf_pages`.
- `"is_scanned_document"` — `True` iff the document is treated as scanned (all pages image-based).
- `"has_mixed_pages"` — `True` when both `selectable_text` and `image` pages are present.
- `"page_types"` — `{ page_number: "selectable_text" | "image" }`.
- `"ocr_engine"` and `"ocr_page_confidences"` — when OCR was used for text extraction.

### `DetectedForm`

Produced by Layer 2. Carries location and confidence; no field values.

```python
@dataclass
class DetectedForm:
    form_id: str
    display_name: str
    page_numbers: list[int]
    confidence: float
```

### `ExtractedForm`

The core output unit. One per detected form in the JSON output.

```python
@dataclass
class ExtractedForm:
    form_id: str
    display_name: str
    page_numbers: list[int]
    confidence: float
    fields: dict[str, Any]
    tax_year: str | None = None          # "2024", "2023" — extracted from form header
    instance_index: int = 0              # For multi-instance forms (Sched C #1, #2...)
    extraction_tier_used: str | None = None  # Audit: which strategy was used
```

> **Note**: `tax_year` and `instance_index` are planned additions. The current implementation does not yet populate these.

---

## 7. JSON Output Schema

### Root envelope

```json
{
  "filename": "tax_package_2024.pdf",
  "total_pages": 8,
  "processed_at": "2026-03-04T14:30:00Z",
  "forms": [ ... ]
}
```

### Per-form object (one entry per detected form)

```json
{
  "form_id": "W-2",
  "display_name": "Form W-2 (Wage and Tax Statement)",
  "tax_year": "2024",
  "instance_index": 0,
  "page_numbers": [1, 2],
  "confidence": 0.95,
  "extraction_tier_used": "pdfplumber",
  "fields": { ... }
}
```

### Field schemas by form

#### Form W-2

```json
{
  "employee_ssn": "XXX-XX-6789",
  "employer_ein": "12-3456789",
  "employee_name": "JOHN A SMITH",
  "employer_name": "ACME CORPORATION",
  "wages_tips_other_compensation_box_1": 82500.00,
  "federal_income_tax_withheld_box_2": 12400.00,
  "social_security_wages_box_3": 82500.00,
  "social_security_tax_withheld_box_4": 5115.00,
  "medicare_wages_tips_box_5": 82500.00,
  "medicare_tax_withheld_box_6": 1196.25,
  "box_12_codes": [
    { "code": "D", "amount": 6500.00 },
    { "code": "W", "amount": 1200.00 }
  ],
  "box_14_other": [
    { "label": "SDI", "amount": 825.00 }
  ],
  "state_wages_box_16": 82500.00,
  "state_income_tax_box_17": 5775.00
}
```

> `box_12_codes` and `box_14_other` are planned additions to the W-2 parser.

#### Form 1099-NEC

```json
{
  "payer_name": "SOME CLIENT LLC",
  "payer_tin": "98-7654321",
  "recipient_tin": "XXX-XX-1234",
  "recipient_name": "JANE B DOE",
  "nonemployee_compensation_box_1": 45000.00,
  "federal_income_tax_withheld_box_4": 0.00
}
```

#### Form 1099-R

```json
{
  "payer_name": "FIDELITY INVESTMENTS",
  "payer_tin": "04-1234567",
  "recipient_tin": "XXX-XX-4321",
  "gross_distribution_box_1": 25000.00,
  "taxable_amount_box_2a": 25000.00,
  "federal_income_tax_withheld_box_4": 5000.00,
  "distribution_code_box_7": "7"
}
```

#### Form 1040

```json
{
  "wages_salaries_tips_line_1a": 82500.00,
  "adjusted_gross_income_line_11": 76000.00,
  "taxable_income_line_15": 58000.00,
  "total_tax_line_24": 9800.00,
  "federal_tax_withheld_line_25a": 12400.00,
  "amount_refunded_line_34": 2600.00,
  "amount_owed_line_37": null
}
```

#### Schedule C

```json
{
  "business_name": "SMITH CONSULTING",
  "gross_receipts_line_1": 95000.00,
  "gross_income_line_7": 95000.00,
  "total_expenses_line_28": 42000.00,
  "net_profit_or_loss_line_31": 53000.00,
  "depreciation_line_13": 3500.00,
  "depletion_line_12": null,
  "meals_entertainment_line_24b": 1200.00,
  "business_use_of_home_line_30": 2400.00
}
```

#### Schedule B *(planned)*

```json
{
  "total_taxable_interest_line_4": 1200.00,
  "ordinary_dividends_line_6": 3400.00,
  "qualified_dividends": 2800.00
}
```

#### Schedule D *(planned)*

```json
{
  "net_short_term_capital_gain_loss_line_7": -500.00,
  "net_long_term_capital_gain_loss_line_15": 8200.00,
  "total_capital_gain_loss_line_16": 7700.00
}
```

#### Schedule E *(planned — multi-instance)*

```json
{
  "property_address": "123 MAIN ST, ANYTOWN, OH 44101",
  "royalty_income_line_4": 0.00,
  "total_income_line_17": 18000.00,
  "total_expenses_line_20": 11000.00,
  "depreciation_depletion_line_18": 4500.00,
  "net_income_loss": 7000.00
}
```

#### Schedule F *(planned)*

```json
{
  "gross_income_line_11": 120000.00,
  "net_profit_loss_line_34": 38000.00,
  "depreciation_line_14": 12000.00
}
```

#### K-1 (Form 1065 — Partnership) *(planned)*

```json
{
  "partnership_name": "SMITH & JONES LLC",
  "partner_ein": "45-6789012",
  "ownership_percentage": 0.50,
  "ordinary_business_income_loss_box_1": 62000.00,
  "net_rental_income_loss_box_2": 0.00,
  "guaranteed_payments_box_4c": 24000.00,
  "self_employment_earnings_box_14": 86000.00
}
```

#### K-1 (Form 1120-S — S-Corporation) *(planned)*

```json
{
  "s_corp_name": "SMITH TECH INC",
  "shareholder_ein": "23-4567890",
  "ownership_percentage": 0.80,
  "ordinary_business_income_loss_box_1": 110000.00,
  "net_rental_income_loss_box_2": 0.00,
  "other_income_loss_box_10": 0.00
}
```

---

## 8. Supported Tax Forms — Roadmap

| Form | Description | Multi-instance | Phase | Status |
|---|---|---|---|---|
| **W-2** | Wage and Tax Statement | Yes (per employer) | 1 | ✅ Implemented |
| **1099-NEC** | Nonemployee Compensation | Yes (per payer) | 1 | ✅ Implemented |
| **1099-R** | Retirement / Pension Distributions | Yes (per payer) | 1 | ✅ Implemented |
| **Form 1040** | U.S. Individual Income Tax Return | No | 1 | ✅ Implemented |
| **Schedule C** | Sole Proprietorship Profit / Loss | Yes (per business) | 1 | ⚠️ Generic regex only |
| **W-2 Box 12/14** | Deferred comp, SDI, mileage codes | — | 1.5 | 🔲 Planned |
| **Tax Year field** | Extracted from form header | — | 1.5 | 🔲 Planned |
| **Schedule B** | Interest and Dividends | No | 2 | 🔲 Planned |
| **Schedule D** | Capital Gains and Losses | No | 2 | 🔲 Planned |
| **Schedule E** | Supplemental Income (Rental / Partnerships) | Yes (per property) | 2 | 🔲 Planned |
| **Schedule F** | Farm Income | No | 2 | 🔲 Planned |
| **Form 1040 Schedule 1** | Additional Income and Adjustments | No | 2 | 🔲 Planned |
| **Form 1098** | Mortgage Interest Statement | Yes (per lender) | 2 | 🔲 Planned |
| **Form 4562** | Depreciation and Amortization | No | 2 | 🔲 Planned |
| **K-1 (Form 1065)** | Partner's Share of Income | Yes (per entity) | 3 | 🔲 Planned |
| **Form 1065** | Partnership Return | No | 3 | 🔲 Planned |
| **K-1 (Form 1120-S)** | Shareholder's Share of Income | Yes (per entity) | 3 | 🔲 Planned |
| **Form 1120-S** | S-Corporation Return | No | 3 | 🔲 Planned |

---

## 9. Project Structure

```
MGICTaxInsight/
├── tax_poc.py                       # CLI entry point
├── requirements.txt
├── DESIGN.md                        # This document
│
├── src/
│   ├── tax_pipeline.py              # Orchestrates all 4 layers
│   │
│   ├── forms/
│   │   ├── registry.py              # FORM_REGISTRY — all FormSchema definitions
│   │   ├── detector.py              # Layer 2: detect_forms()
│   │   └── extractor.py             # Layer 3: extract_forms() + strategy routing
│   │
│   ├── models/
│   │   └── document.py              # ParsedPage, ParsedDocument, ExtractedForm
│   │
│   ├── parsers/                     # One dedicated parser per form
│   │   ├── w2_parser.py             # ✅ Implemented
│   │   ├── form1099nec_parser.py    # ✅ Implemented
│   │   ├── form1099r_parser.py      # ✅ Implemented
│   │   ├── form1040_parser.py       # ✅ Implemented
│   │   ├── schedule_b_parser.py     # 🔲 Phase 2
│   │   ├── schedule_c_parser.py     # 🔲 Phase 2 (promote from generic regex)
│   │   ├── schedule_d_parser.py     # 🔲 Phase 2
│   │   ├── schedule_e_parser.py     # 🔲 Phase 2
│   │   ├── schedule_f_parser.py     # 🔲 Phase 2
│   │   ├── form1098_parser.py       # 🔲 Phase 2
│   │   ├── form4562_parser.py       # 🔲 Phase 2
│   │   ├── k1_1065_parser.py        # 🔲 Phase 3
│   │   ├── form1065_parser.py       # 🔲 Phase 3
│   │   ├── k1_1120s_parser.py       # 🔲 Phase 3
│   │   └── form1120s_parser.py      # 🔲 Phase 3
│   │
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── tesseract_engine.py      # ✅ PDF → 300 DPI image → Tesseract 5 text
│   │
│   ├── strategies/                  # 🔲 Phase 2+: extraction strategy implementations
│   │   ├── base.py                  # IExtractionStrategy protocol
│   │   ├── pdfplumber_strategy.py   # Current approach (wraps dedicated parsers)
│   │   ├── azure_prebuilt_strategy.py
│   │   ├── azure_custom_strategy.py
│   │   ├── azure_custom_strategy.py
│   │   └── llm_strategy.py
│   │
│   └── utils/
│       ├── normalizers.py           # 🔲 Phase 1.5: shared value normalisation helpers
│       └── page_classifier.py       # ✅ Page-level classifier (selectable text vs image)
│
├── tests/
│   ├── test_w2_parser.py
│   ├── test_1099nec_parser.py
│   ├── test_1099r_parser.py
│   ├── test_1040_parser.py
│   └── test_detector.py
│
├── samples/                         # Sample PDFs for development/testing
└── output/                          # Extraction results (gitignored in production)
```

---

## 10. Current Implementation Status

### What Works Today (Phase 1)

| Component | File | State |
|---|---|---|
| CLI entry point | `tax_poc.py` | ✅ Working |
| PDF text extraction | `tax_pipeline.py` | ✅ Working (digital PDFs only) |
| Form detection | `src/forms/detector.py` | ✅ Working |
| Form registry | `src/forms/registry.py` | ✅ Working (5 forms) |
| Field extractor / router | `src/forms/extractor.py` | ✅ Working |
| W-2 dedicated parser | `src/parsers/w2_parser.py` | ✅ Working |
| 1099-NEC dedicated parser | `src/parsers/form1099nec_parser.py` | ✅ Working |
| 1099-R dedicated parser | `src/parsers/form1099r_parser.py` | ✅ Working |
| 1040 dedicated parser | `src/parsers/form1040_parser.py` | ✅ Working |
| Schedule C extraction | Generic regex (no dedicated parser yet) | ⚠️ Limited |
| Scanned PDF support | `src/ocr/tesseract_engine.py` — auto-detected, Tesseract 5 | ✅ Working (partial field coverage on noisy scans) |
| `tax_year` on ExtractedForm | Not yet on dataclass | 🔲 Planned |
| Box 12 / Box 14 on W-2 | Not yet in parser | 🔲 Planned |
| Unit tests | `tests/` exists but empty | 🔲 Planned |

### Known Gaps Discovered from W-2 / MGIC Analysis

1. **`tax_year`** is not extracted or stored anywhere in the data model.
2. **W-2 Box 12** (codes + amounts for deferred comp, mileage, HSA, etc.) is not extracted.
3. **W-2 Box 14** (SDI, union dues, non-taxable sick pay) is not extracted.
4. **Schedule C** has no dedicated parser — runs on generic regex, which is unreliable.
5. **Multiple instances** of the same form in one PDF (e.g. two W-2s, two Schedule Cs) are not yet handled distinctly.

---

## 11. Phased Development Plan

### Phase 1.5 — Enrich Existing Forms (Next)

**Goal**: Make the existing forms complete and production-quality.

**Tasks**:
- [ ] Add `tax_year: str | None` to `ExtractedForm` dataclass
- [ ] Add `instance_index: int` to `ExtractedForm` dataclass  
- [ ] Add `extraction_tier_used: str | None` to `ExtractedForm` dataclass
- [ ] Extend `w2_parser.py`: extract Box 12 (all codes + amounts), Box 14, state boxes (15–17)
- [ ] Update W-2 `FormSchema` in `registry.py` with new field definitions
- [ ] Write a dedicated `schedule_c_parser.py` (replace generic regex)
- [ ] Update `schedule_c_parser.py` to extract: Line 12 (depletion), Line 13 (depreciation), Line 24b (meals), Line 30 (home office)
- [ ] Add `tax_year` extraction to all existing parsers
- [ ] Write unit tests for all Phase 1 parsers
- [ ] Update `tax_poc.py` output to include `tax_year` and `instance_index`

### Phase 2 — Personal Tax Form Coverage

**Goal**: Full personal tax return extraction (all 1040 schedules).

**Tasks**:
- [ ] Add `Schedule B` to registry + dedicated parser (Lines 1–6: interest, dividends)
- [ ] Add `Schedule D` to registry + dedicated parser (Line 16: net capital gain/loss)
- [ ] Add `Schedule E` to registry + dedicated parser (Lines 4, 18, 20 per property; multi-instance)
- [ ] Add `Schedule F` to registry + dedicated parser (Lines 11, 14, 34)
- [ ] Add `Form 1040 Schedule 1` to registry + parser (additional income lines)
- [ ] Add `Form 1098` to registry + parser (mortgage interest, property tax)
- [ ] Add `Form 4562` to registry + parser (depreciation schedules)
- [ ] Implement multi-instance form handling in `extractor.py` (per-form instance grouping)
- [ ] Implement `strategies/` module with `IExtractionStrategy` protocol
- [ ] Implement `AzureDIPrebuiltStrategy` for digital + scanned PDFs

### Phase 3 — Business Entity Forms

**Goal**: Support partnership and S-Corporation returns (requires custom models or LLM).

**Tasks**:
- [ ] Add `K-1 (Form 1065)` to registry + dedicated parser (Boxes 1–14)
- [ ] Add `Form 1065` to registry + dedicated parser (Lines 1–22)
- [ ] Add `K-1 (Form 1120-S)` to registry + dedicated parser (Boxes 1–17)
- [ ] Add `Form 1120-S` to registry + dedicated parser (Lines 1–21)
- [ ] Implement `AzureDICustomStrategy` (custom-trained Azure DI models for K-1, 1065, 1120-S)
- [ ] Implement `LlmExtractionStrategy` (Claude / GPT structured tool call fallback)
- [ ] Add `ownership_percentage` field to K-1 form schemas

### Phase 4 — Scanned PDF Support

**Goal**: Handle image-only (scanned) PDFs.

**Tasks**:
- [x] Implement `TesseractEngine` using Tesseract 5 + PyMuPDF (`src/ocr/tesseract_engine.py`)
- [x] Implement `classify_pdf_pages` (`src/utils/page_classifier.py`) for page-level text vs image classification
- [x] Auto-detect scanned documents in `tax_pipeline.py` using `DocumentClassification.is_scanned_document`
- [x] Wire OCR text into existing detection and extraction layers transparently
- [x] Add `extraction_tier` to JSON output envelope and `extraction_tier_used` per form
- [ ] Improve regex patterns in parsers for OCR-noisy text (Box 3/4 SS wages/tax missed on some scans)
- [ ] Implement `PaddleOCRStrategy` for table-heavy layouts (future improvement)
- [ ] Add confidence-gated routing (pdfplumber → OCR → Azure DI)

---

## 12. Known Limitations & Decisions

| Topic | Decision / Limitation |
|---|---|
| **Scanned PDFs** | Supported via Tesseract 5 OCR (`TesseractEngine`) when `is_scanned_document` is true; page-level classification is available through `page_classifier`. |
| **Multi-page W-2 copies** | W-2 PDFs often include Copy B, Copy C, Copy 2 on separate pages — all values are identical. Current parser takes the first match, which is correct. |
| **Multiple W-2s from different employers** | Currently all W-2 pages are passed to a single parser call. Multi-employer support requires the instance grouping work in Phase 1.5. |
| **Multi-year packages** | Tax packages often contain two years. `tax_year` field extraction (Phase 1.5) is the prerequisite. |
| **No calculations** | Magic Tax Insight returns raw extracted values. All income calculations, MGIC worksheet population, and underwriting logic are the responsibility of the consuming system. |
| **Extraction confidence** | Form-level confidence is set by the detector. Field-level confidence is not yet tracked. Future: add `field_confidence: dict[str, float]` to `ExtractedForm`. |
| **Dependency** | Single runtime dependency: `pdfplumber>=0.11.0`. Azure DI and OCR dependencies are added per phase as needed. |
