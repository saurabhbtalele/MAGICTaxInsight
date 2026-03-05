#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.tax_pipeline import process_tax_package


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tax-poc",
        description="PoC utility: process a tax PDF package and output extracted forms + MGIC subset.",
    )
    parser.add_argument("pdf", type=Path, help="Path to the tax package PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output/tax_poc_result.json"),
        help="Output JSON file (default: output/tax_poc_result.json)",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = process_tax_package(args.pdf)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Tax PoC result written to: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

