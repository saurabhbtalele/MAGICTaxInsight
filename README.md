# Magic Tax Insight

A Python PDF document parser that extracts text and tables using dual OCR engines.

| Engine | Role | Strengths |
|---|---|---|
| **Tesseract 5** | Primary OCR | Fast, accurate on clean documents |
| **PaddleOCR** | Secondary OCR | Better table/layout handling, angle correction |

## How It Works

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

```bash
python3 --version
```

## Installation

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
python main.py document.pdf

# Specify output directory
python main.py document.pdf -o results/

# Parse specific pages (1-based)
python main.py document.pdf -p 1,3,5

# Print extracted text to terminal
python main.py document.pdf --print

# Force a specific engine
python main.py document.pdf --engine tesseract
python main.py document.pdf --engine paddle

# Skip preprocessing (for already clean digital PDFs)
python main.py document.pdf --no-preprocess

# JSON output only
python main.py document.pdf --json-only

# Verbose logging
python main.py document.pdf -v
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
          "bbox": {"x": 100, "y": 50, "width": 300, "height": 40},
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

### Plain text (`output/<filename>_text.txt`)

Full extracted text with page break markers.

## Project Structure

```
MGICTaxInsight/
├── main.py                    # CLI entry point
├── requirements.txt
├── src/
│   ├── config.py              # All configuration dataclasses
│   ├── document_parser.py     # Orchestrator (engine routing + merging)
│   ├── models/
│   │   └── document.py        # ParsedDocument, ParsedPage, TextBlock, TableData
│   ├── parsers/
│   │   ├── base.py            # Abstract OCR parser interface
│   │   ├── tesseract_parser.py
│   │   └── paddle_parser.py
│   └── utils/
│       ├── pdf_utils.py       # PDF → images, metadata, embedded text
│       └── image_utils.py     # OpenCV preprocessing, table region detection
├── tests/
├── samples/                   # Place sample PDFs here
└── output/                    # Generated results
```
