from __future__ import annotations

import dataclasses
from typing import Optional


@dataclasses.dataclass(frozen=True)
class MemoRecord:
    memo_uid: str
    created_at: str
    source_export: str
    source_html: str
    source_memo_ordinal: int
    body_md: str
    image_count: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ImageRecord:
    image_uid: str
    memo_uid: str
    order_in_memo: int
    image_relpath: str
    source_relpath: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class MissingImageRecord:
    memo_uid: str
    image_uid: str
    source_relpath: str
    reason: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class ParseResult:
    memos: list[MemoRecord]
    images: list[ImageRecord]
    missing_images: list[MissingImageRecord]