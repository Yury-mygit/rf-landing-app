"""Markdown → HTML рендеринг для публичной витрины lab.raftforge.art.

mistune c escape=True — inline-HTML в body_md рендерится как текст,
без pass-through. Это защита от XSS на публичном landing'е, где данные
из БД отдаются всем.
"""
import mistune


_md = mistune.create_markdown(escape=True, plugins=["table", "url", "strikethrough"])


def render_md(text: str) -> str:
    """Render markdown to HTML. HTML-теги в исходном тексте экранируются."""
    if not text:
        return ""
    return _md(text)
