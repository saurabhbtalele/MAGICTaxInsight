"""Lightweight document model for the pdfplumber-based tax pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedPage:
    page_number: int
    raw_text: str = ""

    @property
    def full_text(self) -> str:
        return self.raw_text


@dataclass
class ParsedDocument:
    filename: str
    total_pages: int = 0
    pages: list[ParsedPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extracted_forms: list["ExtractedForm"] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n--- Page Break ---\n\n".join(p.full_text for p in self.pages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "total_pages": self.total_pages,
            "forms": [f.to_dict() for f in self.extracted_forms],
        }


@dataclass
class ExtractedForm:
    form_id: str
    display_name: str
    page_numbers: list[int]
    fields: dict[str, Any]
    confidence: float
    tax_year: int | None = None
    instance_index: int = 0
    extraction_tier_used: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_id": self.form_id,
            "display_name": self.display_name,
            "tax_year": self.tax_year,
            "instance_index": self.instance_index,
            "page_numbers": self.page_numbers,
            "confidence": round(self.confidence, 2),
            "extraction_tier_used": self.extraction_tier_used,
            "fields": self.fields,
        }
