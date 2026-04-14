from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Sequence

from .models import ImageRecord, MemoRecord, MissingImageRecord, ParseResult


class StoreWriter:
    def __init__(self, store_root: Path) -> None:
        self.store_root = store_root
        self.memos_path = store_root / "memos.jsonl"
        self.images_path = store_root / "images.jsonl"
        self.missing_path = store_root / "missing_images.jsonl"
        self.images_dir = store_root / "images"

    def write(self, result: ParseResult, raw_root: Path) -> None:
        self.store_root.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self._write_jsonl(self.memos_path, result.memos)
        self._write_jsonl(self.images_path, result.images)
        self._write_jsonl(self.missing_path, result.missing_images)

        self._copy_images(result.images, raw_root)

    @staticmethod
    def _write_jsonl(path: Path, records: Sequence[MemoRecord | ImageRecord | MissingImageRecord]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def _copy_images(self, images: list[ImageRecord], raw_root: Path) -> None:
        for img in images:
            dest = self.store_root.parent / img.image_relpath
            dest.parent.mkdir(parents=True, exist_ok=True)

            source = raw_root / img.source_relpath

            if source.exists() and not dest.exists():
                shutil.copy2(source, dest)