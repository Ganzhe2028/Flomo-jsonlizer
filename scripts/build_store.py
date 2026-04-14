#!/usr/bin/env python3
"""Build the JSONL truth layer from raw flomo HTML exports.

Usage:
    python scripts/build_store.py --raw-root raw --store-root store
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import FlomoParser, StoreWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="Build JSONL truth layer from raw flomo exports")
    parser.add_argument("--raw-root", type=Path, default=Path("raw"), help="Path to raw/ directory")
    parser.add_argument("--store-root", type=Path, default=Path("store"), help="Path to store/ directory")
    args = parser.parse_args()

    raw_root = args.raw_root.resolve()
    store_root = args.store_root.resolve()

    if not raw_root.is_dir():
        print(f"Error: raw directory not found: {raw_root}", file=sys.stderr)
        sys.exit(1)

    parser_engine = FlomoParser(raw_root=raw_root, store_root=store_root)
    result = parser_engine.parse_all()

    writer = StoreWriter(store_root=store_root)
    writer.write(result, raw_root=raw_root)

    print(f"Memos:          {len(result.memos)}")
    print(f"Images:         {len(result.images)}")
    print(f"Missing images: {len(result.missing_images)}")
    print(f"Store written to: {store_root}")


if __name__ == "__main__":
    main()