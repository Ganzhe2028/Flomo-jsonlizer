from src.parser import _extract_batch_label, _format_ordinal, _html_to_markdown, _parse_time, _slugify_user
from bs4 import BeautifulSoup, Tag


def test_extract_batch_label() -> None:
    assert _extract_batch_label("flomo@IsaacBao-20260301") == "20260301"
    assert _extract_batch_label("flomo@SomeUser-20250115") == "20250115"


def test_format_ordinal() -> None:
    assert _format_ordinal(1) == "0001"
    assert _format_ordinal(255) == "0255"
    assert _format_ordinal(9999) == "9999"


def test_slugify_user() -> None:
    assert _slugify_user("IsaacBao") == "isaacbao"
    assert _slugify_user("Some User") == "someuser"
    assert _slugify_user("  Test  ") == "test"


def test_parse_time_standard() -> None:
    soup = BeautifulSoup('<div class="time">2026-03-04 13:06:44</div>', "html.parser")
    time_div = soup.find("div", class_="time")
    assert isinstance(time_div, Tag)
    assert _parse_time(time_div) == "2026-03-04T13:06:44"


def test_parse_time_no_seconds() -> None:
    soup = BeautifulSoup('<div class="time">2026-03-04 13:06</div>', "html.parser")
    time_div = soup.find("div", class_="time")
    assert isinstance(time_div, Tag)
    assert _parse_time(time_div) == "2026-03-04T13:06:00"


def test_parse_time_single_digit_month() -> None:
    soup = BeautifulSoup('<div class="time">2025-1-5 9:30:00</div>', "html.parser")
    time_div = soup.find("div", class_="time")
    assert isinstance(time_div, Tag)
    assert _parse_time(time_div) == "2025-01-05T09:30:00"


def test_html_to_markdown_paragraphs() -> None:
    soup = BeautifulSoup('<div class="content"><p>Hello</p><p>World</p></div>', "html.parser")
    content_div = soup.find("div", class_="content")
    assert isinstance(content_div, Tag)
    assert _html_to_markdown(content_div) == "Hello\n\nWorld"


def test_html_to_markdown_bold() -> None:
    soup = BeautifulSoup('<div class="content"><p>This is <strong>bold</strong> text</p></div>', "html.parser")
    content_div = soup.find("div", class_="content")
    assert isinstance(content_div, Tag)
    assert _html_to_markdown(content_div) == "This is **bold** text"


def test_html_to_markdown_skips_img() -> None:
    soup = BeautifulSoup(
        '<div class="content"><p>Text</p></div><div class="files"><img src="test.png"></div>',
        "html.parser",
    )
    content_div = soup.find("div", class_="content")
    assert isinstance(content_div, Tag)
    result = _html_to_markdown(content_div)
    assert "img" not in result
    assert result == "Text"


def test_html_to_markdown_skips_audio() -> None:
    soup = BeautifulSoup(
        '<div class="content"><p>Text</p><div class="audio-player">audio stuff</div></div>',
        "html.parser",
    )
    content_div = soup.find("div", class_="content")
    assert isinstance(content_div, Tag)
    result = _html_to_markdown(content_div)
    assert "audio" not in result
    assert result == "Text"


def test_html_to_markdown_tags_preserved() -> None:
    soup = BeautifulSoup('<div class="content"><p>Reading #book #thinking</p></div>', "html.parser")
    content_div = soup.find("div", class_="content")
    assert isinstance(content_div, Tag)
    result = _html_to_markdown(content_div)
    assert "#book" in result
    assert "#thinking" in result