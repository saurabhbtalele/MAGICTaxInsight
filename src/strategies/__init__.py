"""Strategy layer for tax form field extraction.

This package contains:
  - IExtractionStrategy protocol (base.py)
  - DoclingExtractionStrategy — AI-powered PDF extraction via IBM Docling
  - LlmExtractionStrategy — Google Gemini LLM fallback with structured outputs
  - LocalExtractionStrategy — existing pdfplumber/regex parsers
  - AzureDIPrebuiltStrategy — mock that simulates Azure DI integration
"""
from src.strategies.base import IExtractionStrategy
from src.strategies.docling_strategy import DoclingExtractionStrategy
from src.strategies.llm_strategy import LlmExtractionStrategy
from src.strategies.local_strategy import LocalExtractionStrategy

__all__ = [
    "IExtractionStrategy",
    "DoclingExtractionStrategy",
    "LlmExtractionStrategy",
    "LocalExtractionStrategy",
]
