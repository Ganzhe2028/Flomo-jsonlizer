import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_store(tmp_path: Path) -> Path:
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    (store_dir / "images").mkdir()
    (store_dir / "memos.jsonl").write_text("", encoding="utf-8")
    (store_dir / "images.jsonl").write_text("", encoding="utf-8")
    (store_dir / "missing_images.jsonl").write_text("", encoding="utf-8")
    return store_dir


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
