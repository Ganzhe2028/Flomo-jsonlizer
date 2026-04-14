#!/usr/bin/env python3
"""Validate the JSONL truth layer.

Usage:
    python scripts/validate_store.py --store-root store
    python scripts/validate_store.py --store-root store --strict
    python scripts/validate_store.py --store-root store --summary
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.validator import StoreValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate JSONL truth layer")
    parser.add_argument("--store-root", type=Path, default=Path("store"))
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors (non-zero exit on any violation)")
    parser.add_argument("--summary", action="store_true",
                        help="Print only summary line, no per-violation detail")
    args = parser.parse_args()

    store_root = args.store_root.resolve()
    project_root = args.project_root.resolve() if args.project_root else None

    validator = StoreValidator(store_root=store_root, project_root=project_root)
    report = validator.validate()

    if args.summary:
        print(report.format_summary())
    else:
        print(report.format_detail())

    if not report.ok:
        sys.exit(1)
    if args.strict and report.warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
