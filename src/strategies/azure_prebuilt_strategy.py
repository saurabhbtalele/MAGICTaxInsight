from __future__ import annotations

from typing import Any

from src.models.document import ParsedDocument
from src.strategies.base import IExtractionStrategy


class AzureDIPrebuiltStrategy(IExtractionStrategy):
    """Mock Azure Document Intelligence prebuilt strategy.

    In production this strategy would call Azure DI with the given model ID
    and map the response into our field schema. For now, it only logs what
    would happen and delegates extraction to a local fallback strategy.
    """

    def __init__(
        self,
        azure_model_id: str,
        fallback_strategy: IExtractionStrategy,
    ) -> None:
        self._azure_model_id = azure_model_id
        self._fallback = fallback_strategy
        self._last_tier_name = "azure_prebuilt_mock"

    @property
    def tier_name(self) -> str:
        return self._last_tier_name

    def extract(
        self,
        form_id: str,
        document: ParsedDocument,
        page_numbers: list[int],
    ) -> dict[str, Any]:
        print(
            f"[azure-mock] Would call Azure DI model "
            f"'{self._azure_model_id}' for form '{form_id}'"
        )

        # Delegate to local strategy so the pipeline stays fully functional.
        fields = self._fallback.extract(form_id, document, page_numbers)

        # Even though the local strategy did the work, we expose that the
        # intended tier is Azure prebuilt (mocked).
        self._last_tier_name = "azure_prebuilt_mock"
        return fields

