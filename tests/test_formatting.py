"""Formatting is part of the API contract. No untrusted HTML should execute."""

from bs4 import BeautifulSoup
from app.formatting import render_answer_html


def test_headings_bold_lists_and_code_render_without_raw_markers():
    md = "## Python path\n\n**Practice** every day.\n\n1. Learn\n2. Build\n\n```python\nprint('hi')\n```"
    html = render_answer_html(md)
    soup = BeautifulSoup(html, "html.parser")
    assert soup.h2.get_text() == "Python path"
    assert soup.strong.get_text() == "Practice"
    assert [li.get_text() for li in soup.select("ol li")] == ["Learn", "Build"]
    assert "print('hi')" in soup.code.get_text()
    assert "**Practice**" not in soup.get_text()


def test_markdown_table_renders_as_real_table():
    html = render_answer_html("| Skill | Reason |\n|---|---|\n| Python | APIs |")
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select("table thead th")) == 2
    assert [x.get_text() for x in soup.select("table tbody td")] == ["Python", "APIs"]


def test_raw_html_is_escaped_instead_of_executed():
    html = render_answer_html('<script>alert(1)</script> <img src=x onerror="alert(1)">')
    soup = BeautifulSoup(html, "html.parser")
    assert soup.find("script") is None
    assert soup.find("img") is None
    assert "&lt;script&gt;" in html


def test_javascript_link_cannot_execute():
    html = render_answer_html("[Surprise](javascript:alert(1))")
    soup = BeautifulSoup(html, "html.parser")
    assert not any((a.get("href") or "").startswith("javascript:") for a in soup.select("a"))


def test_images_are_text_only_and_external_links_are_safe():
    html = render_answer_html("![private](https://tracker.example/pixel) [Docs](https://example.com)")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.find("img") is None
    assert "private" in soup.get_text()
    assert soup.find("a").get("rel") == ["noopener", "noreferrer", "nofollow"]


def test_legacy_br_tags_are_normalized():
    html = render_answer_html("First<br>Second\n\n| Skill | Note |\n|---|---|\n| Python | Do A<br>B |")
    soup = BeautifulSoup(html, "html.parser")
    assert "First" in soup.get_text() and "Second" in soup.get_text()
    assert "&lt;br&gt;" not in html
    assert len(soup.select("table tbody tr")) == 1
