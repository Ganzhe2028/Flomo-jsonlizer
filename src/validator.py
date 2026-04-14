"""Store validator — structural and consistency checks for the JSONL truth layer.

Read-only: never modifies any truth-layer file.
All validation logic lives here; the CLI wrapper is in scripts/validate_store.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class Rule(str, Enum):
    """Maps to the constraint IDs in docs/schema.md (C1–C11) plus extras."""
    C1_MEMO_UID_UNIQUE = "C1"
    C2_IMAGE_UID_UNIQUE = "C2"
    C3_IMAGE_COUNT_CONSISTENT = "C3"
    C4_IMAGE_MEMO_UID_EXISTS = "C4"
    C5_MISSING_MEMO_UID_EXISTS = "C5"
    C6_IMAGE_UID_NO_CROSS = "C6"
    C7_PATH_RELATIVE = "C7"
    C8_IMAGE_FILE_EXISTS = "C8"
    C9_SOURCE_FILE_EXISTS = "C9"
    C10_CREATED_AT_ISO = "C10"
    C11_NO_FRONTMATTER = "C11"
    R1_MEMO_JSONL_PARSEABLE = "R1"
    R2_IMAGE_JSONL_PARSEABLE = "R2"
    R3_MISSING_JSONL_PARSEABLE = "R3"
    R4_EMPTY_KEY_FIELD = "R4"
    R5_MISSING_REQUIRED_FIELD = "R5"


MEMO_FIELDS = {"memo_uid", "created_at", "source_export", "source_html", "source_memo_ordinal", "body_md", "image_count"}
IMAGE_FIELDS = {"image_uid", "memo_uid", "order_in_memo", "image_relpath", "source_relpath"}
MISSING_FIELDS = {"memo_uid", "image_uid", "source_relpath", "reason"}

MEMO_KEY_FIELDS = {"memo_uid", "created_at", "source_export", "source_html", "body_md"}
IMAGE_KEY_FIELDS = {"image_uid", "memo_uid", "image_relpath", "source_relpath"}
MISSING_KEY_FIELDS = {"memo_uid", "image_uid", "source_relpath", "reason"}

IMAGE_PATH_FIELDS = {"image_relpath", "source_relpath"}
MISSING_PATH_FIELDS = {"source_relpath"}

ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


@dataclass(frozen=True)
class Violation:
    rule: Rule
    severity: Severity
    message: str
    table: str
    line: int
    uid: str


@dataclass
class ValidationReport:
    violations: list[Violation] = field(default_factory=list)

    @property
    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == Severity.WARNING]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def format_summary(self) -> str:
        n_errors = len(self.errors)
        n_warnings = len(self.warnings)
        if self.ok:
            return f"✓ Validation passed ({n_warnings} warning(s))"
        return f"✗ Validation failed: {n_errors} error(s), {n_warnings} warning(s)"

    def format_detail(self) -> str:
        lines: list[str] = []
        by_table: dict[str, list[Violation]] = {}
        for v in self.violations:
            by_table.setdefault(v.table, []).append(v)

        for table in ("memos", "images", "missing_images", "cross-table"):
            vs = by_table.get(table)
            if not vs:
                continue
            lines.append(f"\n── {table} ──")
            for v in sorted(vs, key=lambda x: (x.line, x.rule.value)):
                loc = f"line {v.line}" if v.line > 0 else "global"
                uid_part = f" [{v.uid}]" if v.uid else ""
                lines.append(f"  {v.severity.value.upper():7} {v.rule.value:3} {loc:>10}{uid_part}  {v.message}")

        lines.append("")
        lines.append(self.format_summary())
        return "\n".join(lines)


def _load_jsonl(path: Path, table_name: str, report: ValidationReport, rule: Rule) -> list[dict]:
    """Read a JSONL file; record parse failures as violations."""
    records: list[dict] = []
    if not path.exists():
        report.add(Violation(rule=rule, severity=Severity.ERROR,
                             message=f"File not found: {path}", table=table_name, line=0, uid=""))
        return records
    for i, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            report.add(Violation(rule=rule, severity=Severity.ERROR,
                                 message=f"JSON parse error: {exc}", table=table_name, line=i, uid=""))
    return records


class StoreValidator:
    """Validates the JSONL truth layer without modifying it."""

    def __init__(self, store_root: Path, project_root: Path | None = None) -> None:
        self.store_root = store_root
        self.project_root = project_root or store_root.parent
        self.memos_path = store_root / "memos.jsonl"
        self.images_path = store_root / "images.jsonl"
        self.missing_path = store_root / "missing_images.jsonl"

    def validate(self) -> ValidationReport:
        report = ValidationReport()

        memos = _load_jsonl(self.memos_path, "memos", report, Rule.R1_MEMO_JSONL_PARSEABLE)
        images = _load_jsonl(self.images_path, "images", report, Rule.R2_IMAGE_JSONL_PARSEABLE)
        missing = _load_jsonl(self.missing_path, "missing_images", report, Rule.R3_MISSING_JSONL_PARSEABLE)

        if not memos and not images and not missing:
            return report

        self._check_required_fields(memos, "memos", MEMO_FIELDS, report)
        self._check_required_fields(images, "images", IMAGE_FIELDS, report)
        self._check_required_fields(missing, "missing_images", MISSING_FIELDS, report)

        self._check_empty_keys(memos, "memos", MEMO_KEY_FIELDS, report)
        self._check_empty_keys(images, "images", IMAGE_KEY_FIELDS, report)
        self._check_empty_keys(missing, "missing_images", MISSING_KEY_FIELDS, report)

        self._check_uid_unique(memos, "memos", "memo_uid", Rule.C1_MEMO_UID_UNIQUE, report)
        self._check_uid_unique(images, "images", "image_uid", Rule.C2_IMAGE_UID_UNIQUE, report)

        memo_uids = {r.get("memo_uid", "") for r in memos}
        self._check_fk_exists(images, "images", "memo_uid", memo_uids, Rule.C4_IMAGE_MEMO_UID_EXISTS, report)
        self._check_fk_exists(missing, "missing_images", "memo_uid", memo_uids, Rule.C5_MISSING_MEMO_UID_EXISTS, report)

        image_uids_set = {r.get("image_uid", "") for r in images}
        missing_uids_set = {r.get("image_uid", "") for r in missing}
        for uid in image_uids_set & missing_uids_set:
            if uid:
                report.add(Violation(rule=Rule.C6_IMAGE_UID_NO_CROSS, severity=Severity.ERROR,
                                     message="image_uid appears in both images and missing_images",
                                     table="cross-table", line=0, uid=uid))

        self._check_relative_paths(images, "images", IMAGE_PATH_FIELDS, report)
        self._check_relative_paths(missing, "missing_images", MISSING_PATH_FIELDS, report)

        self._check_image_files_exist(images, report)

        self._check_iso8601(memos, report)

        self._check_image_count(memos, images, missing, report)

        return report

    @staticmethod
    def _check_required_fields(records: list[dict], table: str, required: set[str], report: ValidationReport) -> None:
        for i, rec in enumerate(records, start=1):
            missing_fields = required - rec.keys()
            if missing_fields:
                uid = rec.get("memo_uid") or rec.get("image_uid", "")
                report.add(Violation(rule=Rule.R5_MISSING_REQUIRED_FIELD, severity=Severity.ERROR,
                                     message=f"Missing required field(s): {', '.join(sorted(missing_fields))}",
                                     table=table, line=i, uid=uid))

    @staticmethod
    def _check_empty_keys(records: list[dict], table: str, key_fields: set[str], report: ValidationReport) -> None:
        for i, rec in enumerate(records, start=1):
            for fld in sorted(key_fields):
                val = rec.get(fld)
                if val == "":
                    uid = rec.get("memo_uid") or rec.get("image_uid", "")
                    report.add(Violation(rule=Rule.R4_EMPTY_KEY_FIELD, severity=Severity.ERROR,
                                         message=f"Empty string in key field '{fld}'",
                                         table=table, line=i, uid=uid))

    @staticmethod
    def _check_uid_unique(records: list[dict], table: str, uid_field: str, rule: Rule, report: ValidationReport) -> None:
        seen: dict[str, int] = {}
        for i, rec in enumerate(records, start=1):
            uid = rec.get(uid_field, "")
            if uid in seen:
                report.add(Violation(rule=rule, severity=Severity.ERROR,
                                     message=f"Duplicate {uid_field}",
                                     table=table, line=i, uid=uid))
            else:
                seen[uid] = i

    @staticmethod
    def _check_fk_exists(records: list[dict], table: str, fk_field: str,
                         parent_uids: set[str], rule: Rule, report: ValidationReport) -> None:
        for i, rec in enumerate(records, start=1):
            fk_val = rec.get(fk_field, "")
            if fk_val and fk_val not in parent_uids:
                report.add(Violation(rule=rule, severity=Severity.ERROR,
                                     message=f"{fk_field} '{fk_val}' not found in memos",
                                     table=table, line=i, uid=fk_val))

    @staticmethod
    def _check_relative_paths(records: list[dict], table: str, path_fields: set[str], report: ValidationReport) -> None:
        for i, rec in enumerate(records, start=1):
            for fld in sorted(path_fields):
                val = rec.get(fld, "")
                if val and (val.startswith("/") or val.startswith("\\")):
                    uid = rec.get("memo_uid") or rec.get("image_uid", "")
                    report.add(Violation(rule=Rule.C7_PATH_RELATIVE, severity=Severity.ERROR,
                                         message=f"Absolute path in '{fld}': {val}",
                                         table=table, line=i, uid=uid))

    def _check_image_files_exist(self, images: list[dict], report: ValidationReport) -> None:
        for i, rec in enumerate(images, start=1):
            relpath = rec.get("image_relpath", "")
            if not relpath:
                continue
            full_path = self.project_root / relpath
            if not full_path.exists():
                uid = rec.get("image_uid", "")
                report.add(Violation(rule=Rule.C8_IMAGE_FILE_EXISTS, severity=Severity.ERROR,
                                     message=f"Image file not found: {relpath}",
                                     table="images", line=i, uid=uid))

    @staticmethod
    def _check_iso8601(memos: list[dict], report: ValidationReport) -> None:
        for i, rec in enumerate(memos, start=1):
            ts = rec.get("created_at", "")
            if ts and not ISO8601_RE.match(ts):
                uid = rec.get("memo_uid", "")
                report.add(Violation(rule=Rule.C10_CREATED_AT_ISO, severity=Severity.ERROR,
                                     message=f"Invalid ISO 8601 format: '{ts}' (expected YYYY-MM-DDTHH:MM:SS)",
                                     table="memos", line=i, uid=uid))

    @staticmethod
    def _check_image_count(memos: list[dict], images: list[dict], missing: list[dict], report: ValidationReport) -> None:
        img_count_by_memo: dict[str, int] = {}
        for rec in images:
            muid = rec.get("memo_uid", "")
            if muid:
                img_count_by_memo[muid] = img_count_by_memo.get(muid, 0) + 1
        for rec in missing:
            muid = rec.get("memo_uid", "")
            if muid:
                img_count_by_memo[muid] = img_count_by_memo.get(muid, 0) + 1

        for i, rec in enumerate(memos, start=1):
            muid = rec.get("memo_uid", "")
            declared = rec.get("image_count")
            if muid and declared is not None:
                actual = img_count_by_memo.get(muid, 0)
                if declared != actual:
                    report.add(Violation(rule=Rule.C3_IMAGE_COUNT_CONSISTENT, severity=Severity.ERROR,
                                         message=f"image_count={declared} but found {actual} image records (images + missing)",
                                         table="memos", line=i, uid=muid))
