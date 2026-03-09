# Adding New Features

The pipeline relies on a sophisticated 3-Tier architecture and a generalized **Form Registry**.

**Major Benefit**: To add extraction support for a completely new IRS form, you only _have_ to complete Step 1! The system will automatically use Tier 1 (Docling) and Tier 2 (LLM) to extract the data based entirely on your schema design.

You only need to proceed to Steps 2 and 3 if you want to implement a hyper-fast, deterministic Tier 3 (Local Regex) parser for that form.

Here is the step-by-step workflow:

## Step 1: Define the `FormSchema` in `registry.py`

All supported forms live inside `src/forms/registry.py` under the `FORM_REGISTRY` dict. Add a dataclass definition for your new form.

```python
    "Schedule E": FormSchema(
        form_id="Schedule E",
        display_name="Supplemental Income and Loss",
        detection_patterns=["Schedule E", "Supplemental Income and Loss", "Form 1040"],
        supports_multiple_instances=True,
        fields=[
            FormFieldDefinition(name="total_income_line_17", label_patterns=[r"17\s*Total.*income"], value_type="currency"),
        ]
    )
```

---

_If you are satisfied trusting Docling and Gemini for your new form, you can stop here! The system dynamically reads the `FORM_REGISTRY` and will parse the document immediately._

_Continue below only if you are building a custom Tier 3 Regex Parser._

## Step 2: Create a Dedicated Parser (Tier 3)

Create a parsing script inside `src/parsers/` named `<form_id>_parser.py` (e.g. `schedule_e_parser.py`).

```python
import re
from typing import Any
from src.utils.logger import log

def extract_schedule_e(text: str) -> dict[str, Any]:
    log.debug("Attempting precision extraction for Schedule E")

    # Implement custom Regex / pattern seeking logic for this specific form's structural oddities.
    return {"total_income_line_17": 5400.0}
```

## Step 3: Register the Parser

Bind your new parser inside `src/forms/extractor.py` inside the `_DEDICATED_PARSERS` dictionary mapping.

```python
from src.parsers.schedule_e_parser import extract_schedule_e

_DEDICATED_PARSERS = {
    "W-2": extract_w2,
    "1040": extract_1040,
    "Schedule E": extract_schedule_e,
}
```

## Step 4: Test Extractor

Grab a sample from `samples/` that contains your new form.

```bash
./run.sh run samples/schedule-e-test.pdf
```

Check `output/tax_poc_result.json` and ensure your `Form_ID` block correctly populates inside the "forms" array with a high confidence score.

The `tax_pipeline.py` script automatically loops through, executes OCR (if necessary via page classification), discovers the new Schema from the registry, runs your dedicated parser, and serializes the result output dynamically!
