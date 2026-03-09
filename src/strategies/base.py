from __future__ import annotations

from typing import Protocol, Any

from src.models.document import ParsedDocument


class IExtractionStrategy(Protocol):
    @property
    def tier_name(self) -> str:
        """Human-readable name of the extraction tier used."""

        ...

    def extract(
        self,
        form_id: str,
        document: ParsedDocument,
        page_numbers: list[int],
        tax_year: int | None = None,
    ) -> dict[str, Any]:
        """Extract all fields for a detected form."""

        ...
