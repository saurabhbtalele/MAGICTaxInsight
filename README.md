# Magic Tax Insight

A Python PDF document parser that extracts text and tables using dual OCR engines.

| Engine          | Role          | Strengths                                      |
| --------------- | ------------- | ---------------------------------------------- |
| **Tesseract 5** | Primary OCR   | Fast, accurate on clean documents              |
| **PaddleOCR**   | Secondary OCR | Better table/layout handling, angle correction |

## Supported Forms (Phases A–D)

The extractor now supports the following IRS forms with dedicated logic:

| Category | Form ID    | Description                       | Parser Type |
| -------- | ---------- | --------------------------------- | ----------- |
| **Core** | W-2        | Wage and Tax Statement            | PDFPlumber  |
| **Core** | 1040       | U.S. Individual Income Tax Return | PDFPlumber  |
| **B**    | 1099-MISC  | Miscellaneous Income              | PDFPlumber  |
| **B**    | Schedule B | Interest and Ordinary Dividends   | PDFPlumber  |
| **B**    | Schedule C | Profit or Loss from Business      | PDFPlumber  |
| **C**    | Schedule D | Capital Gains and Losses          | PDFPlumber  |
| **C**    | Schedule E | Supplemental Income and Loss      | PDFPlumber  |
| **C**    | Schedule F | Profit or Loss from Farming       | PDFPlumber  |
| **D**    | 1065       | U.S. Return of Partnership Income | PDFPlumber  |
| **D**    | 1120-S     | S-Corp Income Tax Return          | PDFPlumber  |
| **D**    | 1120       | C-Corp Income Tax Return          | PDFPlumber  |
| **Misc** | 1099-NEC   | Nonemployee Compensation          | PDFPlumber  |
| **Misc** | 1099-R     | Distributions From Pensions, etc. | PDFPlumber  |

## Extraction Architecture

1. **Tier 1: Docling Strategy** (AI layout analysis)
2. **Tier 2: LLM Fallback** (Gemini 2.0 Flash)
3. **Tier 3: Local Strategy** (Dedicated Regex/Plumber parsers)

```
PDF → Page Images (PyMuPDF @ 300 DPI)
  → Preprocessing (OpenCV: deskew, denoise, binarize)
    → OCR (Tesseract primary → PaddleOCR fallback/tables)
      → Structured Output (JSON + plain text)
```

**Smart routing:**

- Pages with embedded text are extracted directly (no OCR needed)
- Table regions are automatically detected and routed to PaddleOCR
- If Tesseract confidence is low, PaddleOCR is tried as a fallback
- Results from both engines can be merged (Tesseract text + PaddleOCR tables)

## Prerequisites

### Tesseract 5

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-eng

# Verify
tesseract --version   # Should show 5.x
```

### Python 3.10+

````bash
## Fast Execution Setup (All Platforms)

To make running this easier, we've provided script runners for all operating systems.

### For Windows Users (PowerShell / CMD)
Use the included `run.bat` script:
```cmd
# See all available commands
.\run.bat help

# 1. Build the docker image (Run this first!)
.\run.bat build

# 2. Run the parser on a single PDF (e.g. samples/my_file.pdf)
# Note: Docling OCR is automatically used as the primary engine!
.\run.bat run samples/my_file.pdf

# 3. Run the parser on an entire folder of PDFs (Batch Mode)
.\run.bat batch samples/

# 4. Run all unit tests inside Docker (How to test)
.\run.bat test

# 5. Enter the container for debugging
.\run.bat shell
````

### For Mac & Linux Users

Use either `make` or the `run.sh` script:

```bash
# See all available commands
make help    # OR ./run.sh help

# 1. Build the docker image (Run this first!)
make build   # OR ./run.sh build

# 2. Run the parser on a single PDF (e.g. samples/my_file.pdf)
# Note: Docling OCR is automatically used as the primary engine!
make run samples/my_file.pdf     # OR ./run.sh run samples/my_file.pdf

# 3. Run the parser on an entire folder of PDFs (Batch Mode)
make batch samples/              # OR ./run.sh batch samples/

# 4. Run all unit tests inside Docker (How to test)
make test                        # OR ./run.sh test

# 5. Enter the container for debugging
make shell   # OR ./run.sh shell
```

## How the 3-Tier System Works (including Docling)

When you run the commands above, the system automatically uses our 3-tier architecture:

1. **Tier 1 (Docling)**: The document is first sent to IBM Docling for AI layout analysis and OCR.
2. **Confidence Check**: If Docling is highly confident (>80%), the system stops here and returns the result!
3. **Tier 2 & 3 (LLM / Regex)**: If Docling struggles on a complicated page, it seamlessly falls back to Gemini 2.0 or local Regex parsing.

**You don't need to do anything special to "use Docling" — it happens automatically out of the box!**

## Manual Docker Compose Commands

```bash
# Build the Docker image
docker-compose build

# Run the parser on a sample document
# Place your document in the local 'samples/' folder first
docker-compose run --rm app samples/document.pdf
```

_Note: The `samples/` and `output/` directories are mapped directly to the container. Results will be saved back to your local `output/` folder._

## Manual Installation (Local Environment)

```bash
cd MGICTaxInsight
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Basic — parse a PDF with auto engine selection
python tax_poc.py document.pdf

# Specify output directory
python tax_poc.py document.pdf -o results/

# Parse specific pages (1-based)
python tax_poc.py document.pdf -p 1,3,5

# Print extracted text to terminal
python tax_poc.py document.pdf --print

# Force a specific engine
python tax_poc.py document.pdf --engine tesseract
python tax_poc.py document.pdf --engine paddle

# Skip preprocessing (for already clean digital PDFs)
python tax_poc.py document.pdf --no-preprocess

# JSON output only
python tax_poc.py document.pdf --json-only

# Verbose logging
python tax_poc.py document.pdf -v
```

### Python API

```python
from src.config import AppConfig
from src.document_parser import DocumentParser

config = AppConfig()
parser = DocumentParser(config)

document = parser.parse("path/to/file.pdf")

# Access full extracted text
print(document.full_text)

# Iterate pages
for page in document.pages:
    print(f"Page {page.page_number} ({page.ocr_engine}): {page.avg_confidence:.1f}%")
    for block in page.text_blocks:
        print(f"  [{block.confidence:.0f}%] {block.text}")
    for table in page.tables:
        print(f"  Table: {table.headers}")
        for row in table.rows:
            print(f"    {row}")

# Save to files
parser.save_results(document, output_dir="output")
```

## Output

### JSON (`output/<filename>_parsed.json`)

```json
{
  "filename": "document.pdf",
  "total_pages": 3,
  "pages": [
    {
      "page_number": 1,
      "text_blocks": [
        {
          "text": "Invoice #12345",
          "confidence": 95.2,
          "bbox": { "x": 100, "y": 50, "width": 300, "height": 40 },
          "block_type": "text"
        }
      ],
      "tables": [
        {
          "headers": ["Item", "Qty", "Price"],
          "rows": [["Widget", "10", "$5.00"]],
          "confidence": 91.0
        }
      ],
      "ocr_engine": "tesseract+paddleocr",
      "avg_confidence": 93.1
    }
  ],
  "metadata": { "page_count": 3, "author": "..." }
}
```

## 📘 Deep Dive Documentation

For a comprehensive guide on adding new features, the architectural makeup of the .NET/Python cross-communication, and detailed data extraction lifecycle metrics, please see the `docs/` folder:

- **[Project Index](docs/index.md)**
- **[Developer Run Guide](docs/development-workflow.md)**
- **[Architecture Document](docs/architecture-overview.md)**
- **[Adding New Tax Forms](docs/adding-new-features.md)**
- **[Internal Data Models](docs/data-models.md)**
- **[Core Components overview](docs/core-components.md)**
