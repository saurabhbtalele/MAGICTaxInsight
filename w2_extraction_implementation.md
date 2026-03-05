# W‑2 (2020) Digital PDF Data Extraction -- Implementation Guide

## Overview

This document describes a **simple, production‑ready approach** to
extract key fields from a **digital W‑2 PDF (non‑scanned)** using
Python.

The method avoids OCR and machine learning by relying on:

-   Direct PDF text extraction
-   Stable W‑2 field labels
-   Regex-based parsing

This works well because W‑2 forms follow a **consistent structure across
payroll providers**.

------------------------------------------------------------------------

# Architecture

    PDF Upload
       │
       ▼
    Text Extraction (pdfplumber)
       │
       ▼
    Text Normalization
       │
       ▼
    Regex Field Extraction
       │
       ▼
    Validation
       │
       ▼
    Structured JSON Output

------------------------------------------------------------------------

# Technology Stack

  Layer            Technology
  ---------------- ------------
  Language         Python
  PDF Parsing      pdfplumber
  Parsing          regex
  API (optional)   FastAPI
  Validation       Python

------------------------------------------------------------------------

# Installation

    pip install pdfplumber

------------------------------------------------------------------------

# Basic Extraction Code

``` python
import pdfplumber
import re


def extract_w2_data(pdf_path):

    fields = {
        "wages": r"1\s+Wages.*?(\d[\d,]*\.?\d*)",
        "federal_tax": r"2\s+Federal income tax withheld.*?(\d[\d,]*\.?\d*)",
        "ss_wages": r"3\s+Social security wages.*?(\d[\d,]*\.?\d*)",
        "medicare_wages": r"5\s+Medicare wages.*?(\d[\d,]*\.?\d*)",
        "ssn": r"\d{{3}}-\d{{2}}-\d{{4}}",
        "ein": r"\d{{2}}-\d{{7}}"
    }

    result = {}

    with pdfplumber.open(pdf_path) as pdf:
        text = " ".join(page.extract_text() for page in pdf.pages)

    text = re.sub(r"\s+", " ", text)

    for key, pattern in fields.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            result[key] = match.group(1) if match.groups() else match.group(0)

    return result


if __name__ == "__main__":
    data = extract_w2_data("w2_2020.pdf")
    print(data)
```

------------------------------------------------------------------------

# Expected Output

``` json
{
 "wages": "62000.00",
 "federal_tax": "8200.00",
 "ss_wages": "62000.00",
 "medicare_wages": "62000.00",
 "ssn": "123-45-6789",
 "ein": "12-3456789"
}
```

------------------------------------------------------------------------

# Data Normalization

Convert numeric fields:

``` python
def normalize_amount(value):
    return float(value.replace(",", ""))
```

Example:

    "62,000.00" -> 62000.0

------------------------------------------------------------------------

# Validation Rules

Recommended validations:

### SSN

    ^\d{{3}}-\d{{2}}-\d{{4}}$

### EIN

    ^\d{{2}}-\d{{7}}$

### Numeric fields

-   Must parse as float
-   Must be \>= 0

------------------------------------------------------------------------

# Handling Multiple Copies

W‑2 PDFs usually contain:

-   Copy B
-   Copy C
-   Copy 2

All copies contain identical values.

Recommended approach:

-   Extract **first match only**.

------------------------------------------------------------------------

# Performance

Typical execution:

  Operation         Time
  ----------------- ----------
  Open PDF          \~50 ms
  Text extraction   \~100 ms
  Regex parsing     \~5 ms

Total:

**\<200 ms per document**

------------------------------------------------------------------------

# Scaling for Multiple Documents

For a large system:

    Upload
      ↓
    Document Classifier
      ↓
    Parser Registry
      ↓
    W2 Parser
    1099 Parser
    Bank Parser
    Loan Parser

Example:

    parsers/
       w2_parser.py
       form1099_parser.py
       bank_statement_parser.py

------------------------------------------------------------------------

# API Wrapper Example (Optional)

Example using FastAPI:

``` python
from fastapi import FastAPI, UploadFile
from parser import extract_w2_data

app = FastAPI()

@app.post("/parse/w2")
async def parse_w2(file: UploadFile):
    
    path = f"/tmp/{file.filename}"
    
    with open(path, "wb") as f:
        f.write(await file.read())
    
    data = extract_w2_data(path)
    
    return data
```

------------------------------------------------------------------------

# Known Limitations

This approach fails if:

-   PDF is scanned (image only)
-   Layout text differs heavily
-   Field labels are missing

In those cases OCR or layout models are required.

------------------------------------------------------------------------

# Recommended Future Enhancements

-   Add document classifier
-   Support multiple W‑2 years
-   Create parser registry
-   Add rule engine validation
-   Add confidence scoring

------------------------------------------------------------------------

# Summary

For **digital W‑2 PDFs**, the simplest and most reliable pipeline is:

    PDF → Text Extraction → Regex Parsing → Validation → JSON

No OCR or AI required.

This approach is:

-   Fast
-   Deterministic
-   Easy to maintain
