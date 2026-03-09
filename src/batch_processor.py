"""Async batch processor for concurrent PDF tax form extraction.

Features:
  - Semaphore-limited concurrency (configurable ``max_concurrent``)
  - Per-document timeout (default 120 s)
  - Error isolation — one PDF failure does NOT abort the batch
  - Optional progress callback
  - CLI entry point: ``python -m src.batch_processor /path/to/pdfs/``

Usage::

    import asyncio
    from pathlib import Path
    from src.batch_processor import process_batch

    results = asyncio.run(process_batch([Path("a.pdf"), Path("b.pdf")]))
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.tax_pipeline import process_tax_package

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class BatchResult:
    """Result for a single PDF in a batch run."""

    path: Path
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Batch processor
# ---------------------------------------------------------------------------


async def process_batch(
    pdf_paths: list[Path],
    *,
    max_concurrent: int = 5,
    timeout_seconds: float = 120.0,
    on_progress: Callable[[int, int, BatchResult], None] | None = None,
) -> list[BatchResult]:
    """Process multiple PDFs concurrently with error isolation.

    Parameters
    ----------
    pdf_paths:
        List of PDF file paths to process.
    max_concurrent:
        Maximum number of PDFs processed in parallel.
    timeout_seconds:
        Per-document timeout in seconds.
    on_progress:
        Optional callback ``(completed, total, result)`` called after
        each document finishes.

    Returns
    -------
    list[BatchResult]
        One result per input path, preserving order.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    completed = 0
    total = len(pdf_paths)
    results: list[BatchResult] = [
        BatchResult(path=p, success=False) for p in pdf_paths
    ]

    async def _process_one(index: int, path: Path) -> None:
        nonlocal completed
        async with semaphore:
            try:
                data = await asyncio.wait_for(
                    asyncio.to_thread(process_tax_package, path),
                    timeout=timeout_seconds,
                )
                results[index] = BatchResult(
                    path=path, success=True, data=data
                )
            except asyncio.TimeoutError:
                msg = f"Timeout after {timeout_seconds}s"
                logger.warning("[batch] %s: %s", path.name, msg)
                results[index] = BatchResult(
                    path=path, success=False, error=msg
                )
            except Exception as exc:
                logger.exception("[batch] %s: failed", path.name)
                results[index] = BatchResult(
                    path=path, success=False, error=str(exc)
                )
            finally:
                completed += 1
                if on_progress:
                    on_progress(completed, total, results[index])

    tasks = [_process_one(i, p) for i, p in enumerate(pdf_paths)]
    await asyncio.gather(*tasks)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli_main() -> None:
    """Minimal CLI: ``python -m src.batch_processor <dir_or_files>``."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.batch_processor <pdf_path_or_dir> [...]")
        sys.exit(1)

    paths: list[Path] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.pdf")))
        elif p.is_file():
            paths.append(p)
        else:
            print(f"Warning: skipping {arg} (not found)")

    if not paths:
        print("No PDF files found.")
        sys.exit(1)

    def _on_progress(done: int, total: int, result: BatchResult) -> None:
        status = "✓" if result.success else "✗"
        print(f"  [{done}/{total}] {status} {result.path.name}")

    print(f"Processing {len(paths)} PDF(s)…")
    results = asyncio.run(process_batch(paths, on_progress=_on_progress))

    successes = sum(1 for r in results if r.success)
    failures = len(results) - successes
    print(f"\nDone: {successes} succeeded, {failures} failed.")


if __name__ == "__main__":
    _cli_main()
