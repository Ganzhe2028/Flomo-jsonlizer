"""Tests for src/validator.py — structural and consistency validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.validator import Rule, Severity, StoreValidator, ValidationReport, Violation
from tests.conftest import write_jsonl


def _valid_memo(**overrides) -> dict:
    base = {
        "memo_uid": "flomo-testuser-20250115--0001",
        "created_at": "2025-01-15T10:30:00",
        "source_export": "2025/flomo@TestUser-20250115",
        "source_html": "2025/flomo@TestUser-20250115/2501.html",
        "source_memo_ordinal": 1,
        "body_md": "Hello world",
        "image_count": 0,
    }
    base.update(overrides)
    return base


def _valid_image(**overrides) -> dict:
    base = {
        "image_uid": "flomo-testuser-20250115--0001--01",
        "memo_uid": "flomo-testuser-20250115--0001",
        "order_in_memo": 1,
        "image_relpath": "store/images/2025/2025-01/flomo-testuser-20250115--0001--01.png",
        "source_relpath": "2025/flomo@TestUser-20250115/file/2025-01-15/abc/photo.png",
    }
    base.update(overrides)
    return base


def _valid_missing(**overrides) -> dict:
    base = {
        "memo_uid": "flomo-testuser-20250115--0001",
        "image_uid": "flomo-testuser-20250115--0001--02",
        "source_relpath": "2025/flomo@TestUser-20250115/file/2025-01-15/abc/missing.png",
        "reason": "source_file_missing",
    }
    base.update(overrides)
    return base


class TestValidationReport:
    def test_ok_when_no_errors(self):
        report = ValidationReport()
        assert report.ok
        assert "passed" in report.format_summary()

    def test_not_ok_with_errors(self):
        report = ValidationReport()
        report.add(Violation(rule=Rule.C1_MEMO_UID_UNIQUE, severity=Severity.ERROR,
                             message="dup", table="memos", line=1, uid="x"))
        assert not report.ok
        assert "failed" in report.format_summary()

    def test_warnings_do_not_fail(self):
        report = ValidationReport()
        report.add(Violation(rule=Rule.C1_MEMO_UID_UNIQUE, severity=Severity.WARNING,
                             message="warn", table="memos", line=1, uid="x"))
        assert report.ok


class TestValidStorePasses:
    """A well-formed store should produce zero errors."""

    def test_minimal_valid_store(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image()])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        project_root = tmp_store.parent
        img_path = project_root / _valid_image()["image_relpath"]
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img_path.write_bytes(b"\x89PNG")

        v = StoreValidator(store_root=tmp_store, project_root=project_root)
        report = v.validate()
        assert report.ok, report.format_detail()

    def test_memo_with_no_images(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=0)])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert report.ok


class TestParseFailures:
    """Rules R1–R3: malformed JSONL lines."""

    def test_malformed_memo_jsonl(self, tmp_store: Path):
        (tmp_store / "memos.jsonl").write_text("{bad json}\n", encoding="utf-8")
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(v.rule == Rule.R1_MEMO_JSONL_PARSEABLE for v in report.errors)

    def test_malformed_image_jsonl(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo()])
        (tmp_store / "images.jsonl").write_text("not-json\n", encoding="utf-8")
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(v.rule == Rule.R2_IMAGE_JSONL_PARSEABLE for v in report.errors)

    def test_missing_jsonl_file(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo()])
        write_jsonl(tmp_store / "images.jsonl", [])
        (tmp_store / "missing_images.jsonl").unlink()

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(v.rule == Rule.R3_MISSING_JSONL_PARSEABLE for v in report.errors)


class TestDuplicateUIDs:
    """Rules C1 and C2: uid uniqueness."""

    def test_duplicate_memo_uid(self, tmp_store: Path):
        m = _valid_memo()
        write_jsonl(tmp_store / "memos.jsonl", [m, m])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.C1_MEMO_UID_UNIQUE]
        assert len(violations) >= 1
        assert violations[0].line == 2
        assert violations[0].uid == m["memo_uid"]

    def test_duplicate_image_uid(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        img = _valid_image()
        write_jsonl(tmp_store / "images.jsonl", [img, img])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.C2_IMAGE_UID_UNIQUE]
        assert len(violations) >= 1


class TestReferentialIntegrity:
    """Rules C4, C5: FK existence."""

    def test_image_refs_nonexistent_memo(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(memo_uid="flomo-testuser-20250115--0001", image_count=0)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image(memo_uid="flomo-testuser-20250115--9999")])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.C4_IMAGE_MEMO_UID_EXISTS for x in report.errors)

    def test_missing_image_refs_nonexistent_memo(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=0)])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [_valid_missing(memo_uid="flomo-testuser-99999999--0001")])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.C5_MISSING_MEMO_UID_EXISTS for x in report.errors)


class TestCrossTableConflict:
    """Rule C6: image_uid in both images and missing_images."""

    def test_image_uid_in_both_tables(self, tmp_store: Path):
        uid = "flomo-testuser-20250115--0001--01"
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=2)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image(image_uid=uid)])
        write_jsonl(tmp_store / "missing_images.jsonl", [_valid_missing(image_uid=uid)])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.C6_IMAGE_UID_NO_CROSS for x in report.errors)


class TestPathChecks:
    """Rule C7: relative paths only."""

    def test_absolute_image_relpath(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image(image_relpath="/absolute/path/img.png")])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.C7_PATH_RELATIVE]
        assert len(violations) >= 1
        assert "/absolute/path/img.png" in violations[0].message

    def test_absolute_source_relpath_in_missing(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [_valid_missing(source_relpath="/raw/missing.png")])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.C7_PATH_RELATIVE for x in report.errors)


class TestImageFileExistence:
    """Rule C8: image_relpath file must exist."""

    def test_missing_image_file(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image(image_relpath="store/images/2025/2025-01/nonexistent.png")])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.C8_IMAGE_FILE_EXISTS]
        assert len(violations) >= 1
        assert "nonexistent.png" in violations[0].message


class TestISO8601:
    """Rule C10: created_at format."""

    def test_bad_created_at(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(created_at="2025/01/15 10:30")])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.C10_CREATED_AT_ISO]
        assert len(violations) == 1
        assert violations[0].uid == _valid_memo()["memo_uid"]


class TestImageCountConsistency:
    """Rule C3: image_count matches images + missing_images records."""

    def test_image_count_mismatch(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=5)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image()])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.C3_IMAGE_COUNT_CONSISTENT]
        assert len(violations) == 1
        assert "image_count=5" in violations[0].message
        assert "found 1" in violations[0].message

    def test_image_count_with_missing(self, tmp_store: Path):
        memo = _valid_memo(image_count=3)
        write_jsonl(tmp_store / "memos.jsonl", [memo])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image(order_in_memo=1)])
        write_jsonl(tmp_store / "missing_images.jsonl", [_valid_missing(image_uid=memo["memo_uid"] + "--02", order_in_memo=2) if False else _valid_missing(image_uid=memo["memo_uid"] + "--02")])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        violations = [x for x in report.errors if x.rule == Rule.C3_IMAGE_COUNT_CONSISTENT]
        assert len(violations) == 1


class TestEmptyKeyFields:
    """Rule R4: key fields must not be empty string."""

    def test_empty_memo_uid(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(memo_uid="")])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.R4_EMPTY_KEY_FIELD for x in report.errors)

    def test_empty_image_uid(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        write_jsonl(tmp_store / "images.jsonl", [_valid_image(image_uid="")])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.R4_EMPTY_KEY_FIELD for x in report.errors)


class TestMissingRequiredFields:
    """Rule R5: all required fields must be present."""

    def test_missing_body_md_field(self, tmp_store: Path):
        rec = _valid_memo()
        del rec["body_md"]
        write_jsonl(tmp_store / "memos.jsonl", [rec])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        violations = [x for x in report.errors if x.rule == Rule.R5_MISSING_REQUIRED_FIELD]
        assert any("body_md" in x.message for x in violations)

    def test_missing_image_relpath(self, tmp_store: Path):
        rec = _valid_image()
        del rec["image_relpath"]
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(image_count=1)])
        write_jsonl(tmp_store / "images.jsonl", [rec])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        assert not report.ok
        assert any(x.rule == Rule.R5_MISSING_REQUIRED_FIELD for x in report.errors)


class TestViolationLocationPrecision:
    """Error messages must include line number and uid for precise location."""

    def test_error_reports_line_and_uid(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [
            _valid_memo(memo_uid="flomo-a-20250101--0001"),
            _valid_memo(memo_uid="flomo-a-20250101--0001"),
        ])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        dup = [x for x in report.errors if x.rule == Rule.C1_MEMO_UID_UNIQUE]
        assert len(dup) == 1
        assert dup[0].line == 2
        assert dup[0].uid == "flomo-a-20250101--0001"

    def test_format_detail_contains_line(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(created_at="bad-format")])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        detail = report.format_detail()
        assert "line 1" in detail


class TestSummaryMode:
    def test_summary_shows_only_totals(self, tmp_store: Path):
        write_jsonl(tmp_store / "memos.jsonl", [_valid_memo(created_at="bad")])
        write_jsonl(tmp_store / "images.jsonl", [])
        write_jsonl(tmp_store / "missing_images.jsonl", [])

        v = StoreValidator(store_root=tmp_store, project_root=tmp_store.parent)
        report = v.validate()
        summary = report.format_summary()
        assert "1 error" in summary
        assert "line" not in summary
