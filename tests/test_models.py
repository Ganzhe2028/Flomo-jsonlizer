import json
from pathlib import Path

from src.models import ImageRecord, MemoRecord, MissingImageRecord, ParseResult


def test_memo_record_to_dict() -> None:
    memo = MemoRecord(
        memo_uid="flomo-exampleuser-20260301--0255",
        created_at="2026-03-04T13:06:44",
        source_export="2026/flomo@ExampleUser-20260301",
        source_html="2026/flomo@ExampleUser-20260301/ExampleUser的笔记.html",
        source_memo_ordinal=255,
        body_md="Hello world",
        image_count=2,
    )
    d = memo.to_dict()
    assert d["memo_uid"] == "flomo-exampleuser-20260301--0255"
    assert d["image_count"] == 2
    assert isinstance(d, dict)


def test_image_record_to_dict() -> None:
    img = ImageRecord(
        image_uid="flomo-exampleuser-20260301--0255--01",
        memo_uid="flomo-exampleuser-20260301--0255",
        order_in_memo=1,
        image_relpath="store/images/2026/2026-03/flomo-exampleuser-20260301--0255--01.png",
        source_relpath="2026/flomo@ExampleUser-20260301/file/2026-03-04/1198733/abc.png",
    )
    d = img.to_dict()
    assert d["image_uid"] == "flomo-exampleuser-20260301--0255--01"
    assert d["order_in_memo"] == 1


def test_missing_image_record_to_dict() -> None:
    missing = MissingImageRecord(
        memo_uid="flomo-exampleuser-20260301--0255",
        image_uid="flomo-exampleuser-20260301--0255--02",
        source_relpath="2026/flomo@ExampleUser-20260301/file/2026-03-04/999/def.png",
        reason="source_file_missing",
    )
    d = missing.to_dict()
    assert d["reason"] == "source_file_missing"


def test_parse_result_aggregation() -> None:
    memo = MemoRecord(
        memo_uid="flomo-test-20260101--0001",
        created_at="2026-01-01T10:00:00",
        source_export="2026/flomo@ExampleUser-20260101",
        source_html="2026/flomo@ExampleUser-20260101/test.html",
        source_memo_ordinal=1,
        body_md="test",
        image_count=0,
    )
    result = ParseResult(memos=[memo], images=[], missing_images=[])
    assert len(result.memos) == 1
    assert len(result.images) == 0