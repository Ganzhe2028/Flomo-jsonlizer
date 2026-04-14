import json
from pathlib import Path

from src.models import ImageRecord, MemoRecord, MissingImageRecord
from src.writer import StoreWriter


def test_write_jsonl_memos(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store_root.mkdir(parents=True, exist_ok=True)

    memos = [
        MemoRecord(
            memo_uid="flomo-test-20260101--0001",
            created_at="2026-01-01T10:00:00",
            source_export="2026/flomo@Test-20260101",
            source_html="2026/flomo@Test-20260101/test.html",
            source_memo_ordinal=1,
            body_md="Hello",
            image_count=0,
        )
    ]
    StoreWriter._write_jsonl(store_root / "memos.jsonl", memos)

    lines = (store_root / "memos.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["memo_uid"] == "flomo-test-20260101--0001"


def test_write_jsonl_images(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store_root.mkdir(parents=True, exist_ok=True)
    writer = StoreWriter(store_root=store_root)

    images = [
        ImageRecord(
            image_uid="flomo-test-20260101--0001--01",
            memo_uid="flomo-test-20260101--0001",
            order_in_memo=1,
            image_relpath="store/images/2026/2026-01/flomo-test-20260101--0001--01.png",
            source_relpath="2026/flomo@Test-20260101/file/2026-01-01/123/abc.png",
        )
    ]
    StoreWriter._write_jsonl(store_root / "images.jsonl", images)

    lines = (store_root / "images.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["image_uid"] == "flomo-test-20260101--0001--01"


def test_write_jsonl_utf8(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store_root.mkdir(parents=True, exist_ok=True)

    memos = [
        MemoRecord(
            memo_uid="flomo-test-20260101--0001",
            created_at="2026-01-01T10:00:00",
            source_export="2026/flomo@Test-20260101",
            source_html="2026/flomo@Test-20260101/笔记.html",
            source_memo_ordinal=1,
            body_md="中文内容 #标签",
            image_count=0,
        )
    ]
    StoreWriter._write_jsonl(store_root / "memos.jsonl", memos)

    raw = (store_root / "memos.jsonl").read_text(encoding="utf-8")
    parsed = json.loads(raw.strip())
    assert parsed["body_md"] == "中文内容 #标签"
    assert "笔记" in parsed["source_html"]