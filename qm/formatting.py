"""Turn the light markdown used in content files into email-safe inline-styled HTML.

Supported syntax (deliberately small, so it survives every mail client):

    **bold**   *italic*   [link text](https://...)
    blank line          -> new paragraph (rendered with an empty line between)
    "- item"            -> bulleted list
    "→ item"            -> arrow line (the older Meet-up style)
"""

from __future__ import annotations

import html
import re

FONT = "'Open Sans',Arial,Helvetica,sans-serif"

_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_BULLET = re.compile(r"^\s*[-*•]\s+")
_ARROW = re.compile(r"^\s*→\s*")


def inline(text: str) -> str:
    """Escape text and apply bold, italic and link markup."""
    links: list[str] = []

    def stash(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        links.append(
            f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noreferrer" '
            f'style="color:inherit;text-decoration:underline">{_emphasis(html.escape(label))}</a>'
        )
        return f"\x00{len(links) - 1}\x00"

    out = _emphasis(html.escape(_LINK.sub(stash, text), quote=False))
    return re.sub(r"\x00(\d+)\x00", lambda m: links[int(m.group(1))], out)


def _emphasis(s: str) -> str:
    s = _BOLD.sub(r'<span style="font-weight:700">\1</span>', s)
    return _ITALIC.sub(r'<span style="font-style:italic">\1</span>', s)


def blocks(
    text: str | None,
    *,
    color: str = "rgb(135,135,135)",
    size: int = 14,
    line_height: str = "20px",
    align: str = "left",
    weight: int = 400,
    extra_span_style: str = "",
) -> str:
    """Render paragraphs/bullets as the stacked <div><span> markup Postcards uses."""
    if not text or not text.strip():
        return ""
    div_style = (
        f"text-align:{align};text-align-last:{align};font-family:{FONT};"
        f"font-size:{size}px;line-height:{line_height}"
    )
    span_style = (
        f"font-family:{FONT};color:{color};font-size:{size}px;line-height:{line_height};"
        f"letter-spacing:-0.2px;font-weight:{weight};font-style:normal;{extra_span_style}"
    )
    spacer = f'<div style="{div_style}"><br></div>'

    li_style = f"margin-bottom:0;text-align-last:{align};{span_style}"

    out: list[str] = []
    for para in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.rstrip() for ln in para.strip().splitlines() if ln.strip()]
        if out:
            out.append(spacer)
        text_run: list[str] = []
        bullets: list[str] = []

        def flush_text():
            if text_run:
                body = "<br>".join(inline(t) for t in text_run)
                out.append(f'<div style="{div_style}"><span style="{span_style}">{body}</span></div>')
                text_run.clear()

        def flush_bullets():
            if bullets:
                items = "".join(f'<li style="{li_style}"><span style="{span_style}">{inline(b)}</span></li>' for b in bullets)
                out.append(f'<ul style="margin:0;padding:0 0 0 20px">{items}</ul>')
                bullets.clear()

        for ln in lines:
            if _BULLET.match(ln):
                flush_text()
                bullets.append(_BULLET.sub("", ln, count=1))
            elif _ARROW.match(ln):
                flush_text()
                flush_bullets()
                out.append(f'<div style="{div_style}"><span style="{span_style}">→ {inline(_ARROW.sub("", ln, count=1))}</span></div>')
            else:
                flush_bullets()
                text_run.append(ln.strip())
        flush_text()
        flush_bullets()
    return "".join(out)
