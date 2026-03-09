# Magic Tax Insight Documentation

Welcome to the Magic Tax Insight project documentation. Magic Tax Insight is an intelligent **tax form data extraction service** designed for the mortgage lending industry.

Its single, highly focused responsibility is:

> Accept a tax document PDF &rarr; detect which IRS forms are present &rarr; extract structured fields using a 3-tier system (Docling AI Layout, LLM Fallback, Local Regex) &rarr; return JSON.

## Documentation Index

This documentation is structured to help you understand the architecture, run the system, and contribute new features.

### 1. Architecture & Design

- **[Architecture Overview](architecture-overview.md)**: Explore the Python 3-Tier architecture (Docling, Gemini 2.0, PDFPlumber) and cross-communication.
- **[Data Models](data-models.md)**: Understand the JSON output schemas, the `ParsedDocument` intermediate format, and the specific field outputs for each form.
- **[Core Components](core-components.md)**: Deep dive into the structure of the `src/` directory, including forms, models, and execution strategies.

### 2. Developer Guide

- **[Development Workflow](development-workflow.md)**: Learn how to set up the project locally across Windows, Mac, and Linux using Docker, cross-platform script runners, and where to find your Loguru rotating JSON logs.
- **[Adding New Features](adding-new-features.md)**: A step-by-step guide to adding support for new IRS forms, registering parsers, and handling complex PDF logic.

## Project Structure at a Glance

```
MGICTaxInsight/
├── docs/                            # The documentation you are reading now
├── src/                             # Core Python application logic
│   ├── forms/                       # Detectors, extractors, and field registries
│   ├── models/                      # Domain dataclass models
│   ├── ocr/                         # OCR capability (Tesseract)
│   ├── parsers/                     # Dedicated regex parsing scripts for specific forms
│   ├── strategies/                  # Future LLM / Azure DI integration fallback logic
│   └── utils/                       # Shared utilities like Loguru and Page Classifiers
├── samples/                         # Sample mock PDFs to test the tool against
├── output/                          # Loguru JSON runtime logs and JSON output files
├── tax_poc.py                       # CLI endpoint for extraction logic
├── docker-compose.yml               # Docker configurations for seamless isolated running
├── Makefile                         # Native command runner (Mac / Linux)
├── run.bat                          # Native command runner (Windows)
└── run.sh                           # Additional script runner
```

## Explicit Scope Boundaries

| In Scope                                   | Out of Scope                     |
| ------------------------------------------ | -------------------------------- |
| Detecting IRS form types within a PDF      | Income calculations              |
| Extracting raw field values from each form | MGIC worksheet population        |
| Normalising values (currency, SSN, dates)  | Underwriting logic               |
| Confidence scoring per form/field          | Cross-document validation        |
| Structured JSON output                     | Mortgage-specific business rules |
| Handling multiple forms in one PDF         | LOS / CRM integration            |

The consuming system (e.g. a .NET orchestration service or an MGIC calculation engine) is responsible for using the extracted data. Magic Tax Insight **only** extracts and returns it.
