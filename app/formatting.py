"""Render model Markdown into safe, readable HTML for the browser.

The model is NOT trusted HTML. Mistune's escape=True turns raw tags into text
and neutralizes unsafe URLs. Remote images are rendered as alt text so a model
cannot cause a browser to automatically load third-party tracking images.
"""

from html import escape
import re

import mistune


class ChatHTMLRenderer(mistune.HTMLRenderer):
    def __init__(self):
        super().__init__(escape=True, allow_harmful_protocols=False)

    def image(self, text: str, url: str, title: str | None = None) -> str:
        # Do not load user/model-supplied remote images inside the chatbot.
        return escape(text, quote=False)

    def link(self, text: str, url: str, title: str | None = None) -> str:
        # Mistune validates protocols before passing the URL here.
        link_html = super().link(text, url, title)
        return link_html.replace('<a ', '<a rel="noopener noreferrer nofollow" target="_blank" ', 1)


markdown = mistune.create_markdown(
    renderer=ChatHTMLRenderer(),
    plugins=["table", "strikethrough", "url"],
)

_BR = re.compile(r"\\?<br\s*/?>", re.IGNORECASE)


def render_answer_html(answer: str) -> str:
    """Convert Markdown, including benign legacy line breaks, to escaped HTML."""
    clean_lines = []
    for line in answer.replace("\r\n", "\n").split("\n"):
        # Inside a markdown table, don't turn a cell's <br> into a new row.
        replacement = " · " if line.lstrip().startswith("|") else "\n"
        clean_lines.append(_BR.sub(replacement, line))
    text = "\n".join(clean_lines)
    return markdown(text)
