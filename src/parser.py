from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Optional

from bs4 import BeautifulSoup, Tag

from .models import ImageRecord, MemoRecord, MissingImageRecord, ParseResult


def _discover_html_files(batch_dir: Path) -> list[Path]:
    html_files = [
        f
        for f in batch_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".html" and f.name != ".DS_Store"
    ]
    return sorted(html_files)


def _extract_user_name(soup: BeautifulSoup) -> str:
    name_div = soup.find("div", class_="name")
    if name_div is None:
        raise ValueError("Cannot find <div class='name'> in HTML — not a valid flomo export")
    text = name_div.get_text(strip=True)
    if text.startswith("@"):
        text = text[1:]
    return text


def _slugify_user(name: str) -> str:
    return name.strip().replace(" ", "").lower()


def _extract_batch_label(batch_dir_name: str) -> str:
    pattern = r"flomo@(.+?)-(\d{8})"
    match = re.search(pattern, batch_dir_name)
    if not match:
        raise ValueError(f"Cannot parse batch label from directory: {batch_dir_name}")
    return match.group(2)


def _html_to_markdown(content_div: Tag) -> str:
    parts: list[str] = []

    for element in content_div.children:
        if isinstance(element, str):
            text = element.strip()
            if text:
                parts.append(text)
            continue

        if not isinstance(element, Tag):
            continue

        tag = element.name

        if tag == "p":
            inner = _process_inline(element)
            if inner:
                parts.append(inner)

        elif tag == "br":
            parts.append("")

        elif tag in ("strong", "b"):
            parts.append(f"**{_get_inner_text(element)}**")

        elif tag in ("em", "i"):
            parts.append(f"*{_get_inner_text(element)}*")

        elif tag == "a":
            href = element.get("href", "")
            link_text = _get_inner_text(element)
            if href:
                parts.append(f"[{link_text}]({href})")
            else:
                parts.append(link_text)

        elif tag == "img":
            pass

        elif tag == "div":
            class_list = element.get("class")
            if isinstance(class_list, list) and ("files" in class_list or "audio-player" in class_list):
                continue
            parts.append(_html_to_markdown(element))

    while parts and parts[-1] == "":
        parts.pop()
    while parts and parts[0] == "":
        parts.pop(0)

    return "\n\n".join(parts)


def _process_inline(element: Tag) -> str:
    parts: list[str] = []
    for child in element.children:
        if isinstance(child, str):
            text = child
            parts.append(text)
            continue
        if not isinstance(child, Tag):
            continue
        tag = child.name
        if tag in ("strong", "b"):
            parts.append(f"**{_get_inner_text(child)}**")
        elif tag in ("em", "i"):
            parts.append(f"*{_get_inner_text(child)}*")
        elif tag == "a":
            href = child.get("href", "")
            link_text = _get_inner_text(child)
            if href:
                parts.append(f"[{link_text}]({href})")
            else:
                parts.append(link_text)
        elif tag == "code":
            parts.append(f"`{_get_inner_text(child)}`")
        elif tag == "img":
            pass
        else:
            parts.append(_get_inner_text(child))
    return "".join(parts).strip()


def _get_inner_text(tag: Tag) -> str:
    return tag.get_text(strip=True)


def _parse_time(time_div: Tag) -> Optional[str]:
    raw = time_div.get_text(strip=True)
    pattern = r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2}):?(\d{2})?"
    m = re.match(pattern, raw)
    if not m:
        return None
    year, month, day, hour, minute, second = m.groups()
    second = second or "00"
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}T{int(hour):02d}:{minute}:{int(second):02d}"


def _format_ordinal(n: int) -> str:
    return f"{n:04d}"


class FlomoParser:
    def __init__(self, raw_root: Path, store_root: Path) -> None:
        self.raw_root = raw_root
        self.store_root = store_root

    def parse_all(self) -> ParseResult:
        all_memos: list[MemoRecord] = []
        all_images: list[ImageRecord] = []
        all_missing: list[MissingImageRecord] = []

        batch_dirs = self._discover_batches()
        for batch_dir in batch_dirs:
            result = self.parse_batch(batch_dir)
            all_memos.extend(result.memos)
            all_images.extend(result.images)
            all_missing.extend(result.missing_images)

        all_memos.sort(key=lambda m: m.memo_uid)
        all_images.sort(key=lambda i: i.image_uid)
        all_missing.sort(key=lambda m: (m.memo_uid, m.image_uid))

        return ParseResult(memos=all_memos, images=all_images, missing_images=all_missing)

    def parse_batch(self, batch_dir: Path) -> ParseResult:
        html_files = _discover_html_files(batch_dir)
        if not html_files:
            raise ValueError(f"No HTML files found in {batch_dir}")

        batch_dir_name = batch_dir.name
        batch_label = _extract_batch_label(batch_dir_name)
        source_export = _to_posix(batch_dir.relative_to(self.raw_root))

        first_html = html_files[0]
        source_html_rel = _to_posix(first_html.relative_to(self.raw_root))

        with open(first_html, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        user_display = _extract_user_name(soup)
        user_slug = _slugify_user(user_display)

        memo_divs = soup.find_all("div", class_="memo")

        memos: list[MemoRecord] = []
        images: list[ImageRecord] = []
        missing: list[MissingImageRecord] = []

        for ordinal_1, memo_div in enumerate(memo_divs, start=1):
            time_div = memo_div.find("div", class_="time")
            content_div = memo_div.find("div", class_="content")

            created_at = _parse_time(time_div) if time_div else "1970-01-01T00:00:00"
            assert isinstance(created_at, str)
            body_md = _html_to_markdown(content_div) if content_div else ""

            memo_uid = f"flomo-{user_slug}-{batch_label}--{_format_ordinal(ordinal_1)}"

            img_tags = memo_div.find_all("img")
            img_records: list[ImageRecord] = []
            missing_records: list[MissingImageRecord] = []

            for img_order, img_tag in enumerate(img_tags, start=1):
                src_raw = img_tag.get("src")
                if not src_raw or not isinstance(src_raw, str):
                    continue

                source_relpath = _to_posix(PurePosixPath(src_raw))

                order_str = f"{img_order:02d}"
                image_uid = f"{memo_uid}--{order_str}"

                year_month_match = re.search(r"(\d{4})-(\d{2})", source_relpath)
                if year_month_match:
                    year = year_month_match.group(1)
                    year_month = f"{year}-{year_month_match.group(2)}"
                else:
                    year = "1970"
                    year_month = "1970-01"

                source_abs = batch_dir / str(source_relpath)
                ext = PurePosixPath(source_relpath).suffix or ".png"

                if source_abs.exists():
                    image_relpath = f"store/images/{year}/{year_month}/{image_uid}{ext}"
                    img_records.append(
                        ImageRecord(
                            image_uid=image_uid,
                            memo_uid=memo_uid,
                            order_in_memo=img_order,
                            image_relpath=image_relpath,
                            source_relpath=f"{source_export}/{source_relpath}",
                        )
                    )
                else:
                    missing_records.append(
                        MissingImageRecord(
                            memo_uid=memo_uid,
                            image_uid=image_uid,
                            source_relpath=f"{source_export}/{source_relpath}",
                            reason="source_file_missing",
                        )
                    )

            image_count = len(img_records) + len(missing_records)

            memos.append(
                MemoRecord(
                    memo_uid=memo_uid,
                    created_at=created_at,
                    source_export=source_export,
                    source_html=source_html_rel,
                    source_memo_ordinal=ordinal_1,
                    body_md=body_md,
                    image_count=image_count,
                )
            )
            images.extend(img_records)
            missing.extend(missing_records)

        return ParseResult(memos=memos, images=images, missing_images=missing)

    def _discover_batches(self) -> list[Path]:
        batch_dirs: list[Path] = []
        for year_dir in sorted(self.raw_root.iterdir()):
            if not year_dir.is_dir() or year_dir.name.startswith("."):
                continue
            for sub in sorted(year_dir.iterdir()):
                if not sub.is_dir():
                    continue
                if sub.name.startswith("flomo@"):
                    batch_dirs.append(sub)
                else:
                    for candidate in sorted(sub.iterdir()):
                        if candidate.is_dir() and candidate.name.startswith("flomo@"):
                            batch_dirs.append(candidate)
        return batch_dirs


def _to_posix(path: Path | PurePosixPath) -> str:
    return PurePosixPath(str(path)).as_posix()