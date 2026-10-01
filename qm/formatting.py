"""Turn the light markdown used in content files into email-safe inline-styled HTML.

Supported syntax (deliberately small, so it survives every mail client):

    **bold**   *italic*   [link text](https://...)
    blank line          -> new paragraph (rendered with an empty line between)
    "- item" / "→ item" -> arrow bullet, matching the newsletter's house style
"""

import html
import re

FONT = "'Open Sans',Arial,Helvetica,sans-serif"

_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_BULLET = re.compile(r"^\s*(?:[-*•]|→)\s+")


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

    out: list[str] = []
    for para in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.rstrip() for ln in para.strip().splitlines() if ln.strip()]
        if out:
            out.append(spacer)
        if all(_BULLET.match(ln) for ln in lines):
            for ln in lines:
                body = inline(_BULLET.sub("", ln, count=1))
                out.append(f'<div style="{div_style}"><span style="{span_style}">→ {body}</span></div>')
        else:
            body = "<br>".join(inline(ln.strip()) for ln in lines)
            out.append(f'<div style="{div_style}"><span style="{span_style}">{body}</span></div>')
    return "".join(out)
