import json
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from src.parser import FlomoParser
from src.writer import StoreWriter


SAMPLE_HTML = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<div class="name">@TestUser</div>
<div class="date">于 2026-3-4 导出 3 条 MEMO</div>

<div class="memo">
  <div class="time">2026-03-01 10:00:00</div>
  <div class="content"><p>First memo with <strong>bold</strong> text</p></div>
</div>

<div class="memo">
  <div class="time">2026-03-02 14:30:00</div>
  <div class="content"><p>Second memo with an image</p></div>
  <div class="files">
    <img src="file/2026-03-02/abc123/photo.png">
  </div>
</div>

<div class="memo">
  <div class="time">2026-03-03 09:15:00</div>
  <div class="content"><p>Third memo #tag1 #tag2</p></div>
  <div class="files">
    <img src="file/2026-03-03/def456/missing.jpg">
    <img src="file/2026-03-03/ghi789/audio_cover.png">
  </div>
</div>
</body>
</html>
"""


def _setup_raw_dir(tmp_path: Path) -> Path:
    raw_root = tmp_path / "raw"
    batch_dir = raw_root / "2026" / "flomo@TestUser-20260304"
    batch_dir.mkdir(parents=True)
    (batch_dir / "TestUser的笔记.html").write_text(SAMPLE_HTML, encoding="utf-8")

    file_dir = batch_dir / "file" / "2026-03-02" / "abc123"
    file_dir.mkdir(parents=True)
    (file_dir / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    file_dir2 = batch_dir / "file" / "2026-03-03" / "ghi789"
    file_dir2.mkdir(parents=True)
    (file_dir2 / "audio_cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    return raw_root


def test_end_to_end_parse_and_write(tmp_path: Path) -> None:
    raw_root = _setup_raw_dir(tmp_path)
    store_root = tmp_path / "store"

    parser = FlomoParser(raw_root=raw_root, store_root=store_root)
    result = parser.parse_all()

    writer = StoreWriter(store_root=store_root)
    writer.write(result, raw_root=raw_root)

    assert (store_root / "memos.jsonl").exists()
    assert (store_root / "images.jsonl").exists()
    assert (store_root / "missing_images.jsonl").exists()

    memos_lines = (store_root / "memos.jsonl").read_text(encoding="utf-8").strip().split("\n")
    images_lines = (store_root / "images.jsonl").read_text(encoding="utf-8").strip().split("\n")
    missing_lines = (store_root / "missing_images.jsonl").read_text(encoding="utf-8").strip().split("\n")

    assert len(memos_lines) == 3
    assert len(images_lines) == 2
    assert len(missing_lines) == 1

    memo_1 = json.loads(memos_lines[0])
    assert memo_1["memo_uid"] == "flomo-testuser-20260304--0001"
    assert memo_1["created_at"] == "2026-03-01T10:00:00"
    assert "**bold**" in memo_1["body_md"]
    assert memo_1["image_count"] == 0

    memo_2 = json.loads(memos_lines[1])
    assert memo_2["memo_uid"] == "flomo-testuser-20260304--0002"
    assert memo_2["image_count"] == 1

    memo_3 = json.loads(memos_lines[2])
    assert memo_3["memo_uid"] == "flomo-testuser-20260304--0003"
    assert memo_3["image_count"] == 2
    assert "#tag1" in memo_3["body_md"]
    assert "#tag2" in memo_3["body_md"]

    img_1 = json.loads(images_lines[0])
    assert img_1["image_uid"] == "flomo-testuser-20260304--0002--01"
    assert img_1["memo_uid"] == "flomo-testuser-20260304--0002"
    assert img_1["order_in_memo"] == 1
    assert "store/images/2026/2026-03/" in img_1["image_relpath"]
    assert img_1["image_relpath"].endswith(".png")

    img_2 = json.loads(images_lines[1])
    assert img_2["image_uid"] == "flomo-testuser-20260304--0003--02"

    missing_1 = json.loads(missing_lines[0])
    assert missing_1["image_uid"] == "flomo-testuser-20260304--0003--01"
    assert missing_1["reason"] == "source_file_missing"


def test_end_to_end_image_files_copied(tmp_path: Path) -> None:
    raw_root = _setup_raw_dir(tmp_path)
    store_root = tmp_path / "store"

    parser = FlomoParser(raw_root=raw_root, store_root=store_root)
    result = parser.parse_all()

    writer = StoreWriter(store_root=store_root)
    writer.write(result, raw_root=raw_root)

    images_lines = (store_root / "images.jsonl").read_text(encoding="utf-8").strip().split("\n")
    for line in images_lines:
        rec = json.loads(line)
        img_path = tmp_path / rec["image_relpath"]
        assert img_path.exists(), f"Image file missing: {img_path}"


def test_end_to_end_no_absolute_paths(tmp_path: Path) -> None:
    raw_root = _setup_raw_dir(tmp_path)
    store_root = tmp_path / "store"

    parser = FlomoParser(raw_root=raw_root, store_root=store_root)
    result = parser.parse_all()

    writer = StoreWriter(store_root=store_root)
    writer.write(result, raw_root=raw_root)

    for jsonl_name in ("memos.jsonl", "images.jsonl", "missing_images.jsonl"):
        lines = (store_root / jsonl_name).read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            rec = json.loads(line)
            for key, value in rec.items():
                if isinstance(value, str) and ("/" in value):
                    assert not value.startswith("/"), f"Absolute path found: {key}={value} in {jsonl_name}"


def test_end_to_end_uid_format(tmp_path: Path) -> None:
    raw_root = _setup_raw_dir(tmp_path)
    store_root = tmp_path / "store"

    parser = FlomoParser(raw_root=raw_root, store_root=store_root)
    result = parser.parse_all()

    for memo in result.memos:
        assert memo.memo_uid.startswith("flomo-")
        assert "--" in memo.memo_uid
        parts = memo.memo_uid.split("--")
        assert len(parts) == 2
        assert parts[1].isdigit()
        assert len(parts[1]) == 4

    for img in result.images:
        memo_uids = {m.memo_uid for m in result.memos}
        assert img.memo_uid in memo_uids
        assert img.image_uid.startswith(img.memo_uid + "--")
        assert img.image_uid.count("--") >= 2