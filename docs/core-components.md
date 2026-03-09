# Core Components

The Magic Tax Insight Python engine lives entirely within the `src/` directory.

## Directory Structure

```text
src/
├── forms/
│   ├── detector.py      # Identifies form types
│   ├── extractor.py     # Invokes the StrategyFactory
│   └── registry.py      # Master dictionary storing `FormSchema`s
├── mgic/                    # MGIC-specific worksheet calculations
├── models/
│   └── document.py      # All domain dataclasses
├── ocr/
│   └── tesseract_engine.py  # Legacy wrapper for old components
├── parsers/                 # Tier 3
│   ├── form1040_parser.py
│   ├── form1099nec_parser.py
│   └── ... (many more)
├── strategies/
│   ├── base.py                   # Strategy interfaces
│   ├── strategy_factory.py       # Decides which strategy to fire
│   ├── docling_strategy.py       # Tier 1 (AI Layout)
│   ├── llm_strategy.py           # Tier 2 (Gemini 2.0)
│   └── local_strategy.py         # Tier 3 (Regex Parsers)
├── utils/
│   ├── logger.py            # Loguru configuration
│   ├── normalizers.py       # Helper functions to sanitize string text to Int/Float/Currency
│   └── page_classifier.py   # Analyzes a PDF page to see if it is a true PDF or a Scanned Image
└── tax_pipeline.py          # The orchestrator that chains all these components together
```

## How It Boots Up

When the command `tax_poc.py samples/file.pdf` is executed:

1. `tax_poc.py` parses the arguments.
2. It invokes `process_tax_package` from `tax_pipeline.py`.
3. `tax_pipeline.py` relies on `utils/page_classifier.py` and `ocr/tesseract_engine.py` to get textual strings.
4. `tax_pipeline.py` executes `detect_forms` from `forms/detector.py`, giving it access to `forms/registry.py`.
5. Finally, it executes `extract_forms`, which bounces the request to a script inside the `parsers/` directory matching the form type.
